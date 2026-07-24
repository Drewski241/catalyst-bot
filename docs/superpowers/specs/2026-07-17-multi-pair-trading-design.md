# Multi-Pair Trading Design

Date: 2026-07-17  
Status: Approved direction — Phase 1 in progress  
Goal: Run multiple CAT/XCH trading pairs concurrently in **one CATalyst process on one machine** (one Sage wallet), without requiring multiple computers or multiple app instances.

---

## Purpose

CATalyst today is a hard single-active-pair product. Users who want to market-make several CATs must stop the bot, switch pair, and restart. This design defines how to move from that model to true concurrent multi-pair trading while respecting the shared XCH wallet, desktop singleton, and existing DB shape.

---

## Current constraints (why this is hard)

| Layer | Today | Implication |
|-------|-------|-------------|
| Config | Singular `CAT_ASSET_ID`, `CAT_*`, ladder/spread knobs in one `.env` / `cfg` | Pair B inherits pair A’s economics unless overwritten |
| Runtime | One `api_server.bot` / one `BotLoop` | No concurrent ladders |
| Active pair | `_active_cat` global; `POST /api/cat/select` **409 if bot running** | Switch requires stop |
| XCH | `XCH_RESERVE`, fee pool, XCH tier coins, topup pool are process-global | Two loops would both believe they own the same XCH |
| Coins table | `wallet_type` in (`xch`,`cat`) only — **no `asset_id`** | Multiple CAT inventories would collide |
| Wallet | `wallet_sage._CAT_ASSET_ID` module singleton | Ambiguous CAT RPCs under multi-pair |
| Desktop | Instance lock + one Flask port | Multiple full app instances are the wrong primary model |
| UI | Single `<select id="catSelector">`; “chosen once for the whole app” | Needs a pairs panel |

History is partially ready: `offers`, `fills`, `inventory`, and `price_history` already carry `cat_asset_id` / `asset_id`. Runtime is not.

---

## Non-goals (first concurrent release)

- Cross-CAT pairs (CAT/CAT); quote asset remains XCH
- Separate wallets / fingerprints per pair
- Multiple Flask ports or multiple desktop windows as the primary UX
- Automatic portfolio rebalancing across pairs (beyond hard XCH allocation caps)

---

## Decision: process model

**Recommended: one process, multiple `PairRuntime`s (Option A).**

Keep a single desktop app, Flask control plane, SQLite DB, Sage RPC session, and shared XCH capital/fee layer. Run one trading loop per enabled pair, each with isolated pair config and risk/price/offer state.

```text
┌─────────────────────────────────────────────────────────────┐
│ CATalyst process                                            │
│  Flask + SSE + GUI                                          │
│  Wallet RPC (Sage) ─── wallet_op_lock                       │
│  SQLite (WAL)                                               │
│  SharedXchLedger + FeeCoinAllocator                         │
│                                                             │
│  PairRuntime[SBX] ── BotLoop' ── offers/risk/price/amm      │
│  PairRuntime[MZ]  ── BotLoop' ── offers/risk/price/amm      │
│  PairRuntime[...]                                           │
└─────────────────────────────────────────────────────────────┘
```

### Rejected as primary: multiple app instances / subprocesses

The desktop singleton lock, one Flask port, one coin-prep worker model, and one XCH UTXO set make multiple writers dangerous (mempool conflicts, DB races, double-spend risk). Subprocesses only work with a strict external wallet lock — which collapses back into “one coordinator process.”

---

## Core data model

### `PairConfig` (persisted, keyed by `cat_asset_id`)

| Field group | Contents |
|-------------|----------|
| Identity | `asset_id`, `ticker_id`, `name`, `decimals`, `tibet_pair_id`, `cat_wallet_id` |
| Trading | liquidity mode, spreads, max active counts, tier sizes/counts, hard min/max, inventory knobs |
| Capital | `cat_reserve`, `xch_budget_mojos` (hard allocation slice), optional topup slices, CAT coin size targets |
| Flags | `enabled`, `auto_start` |

### `PairRuntime` (in-memory)

- `config: PairConfig`
- Pair-scoped trading loop (today’s `BotLoop`, but pair-injected)
- Per-pair modules: offer manager, risk manager, price engine instance, AMM monitor, fill tracker view
- Status: `running`, last mid, open counts, last error

### `ProcessShared`

- Wallet RPC + **wallet operation mutex**
- Flask / EventBus / logging
- DB connection factory
- **SharedXchLedger**: wallet `XCH_RESERVE` floor + per-pair `xch_budget_mojos` + unallocated remainder
- **FeeCoinAllocator**: one fee pool, serialized checkout/return
- Tibet `/pairs` list cache (already module-global)

---

## Hard problem: shared XCH

XCH is the scarce shared resource. Concurrent pairs must not each believe they own the full spendable balance.

### Rules

1. **Wallet floor:** `XCH_RESERVE` remains process-global (“never spend below this”).
2. **Per-pair budget:** each enabled pair gets `xch_budget_mojos`. Sum of budgets ≤ spendable − floor − fee buffer.
3. **Fee buffer:** reserved for create/cancel fees; owned by `FeeCoinAllocator`, not by any pair.
4. **Over-allocation rejected** at enable/start time; Smart Settings becomes allocation-aware.
5. **CAT capital** is naturally per-pair (different asset IDs).

### Coin / prep implications

- `coins` table must gain `asset_id` (or equivalent) so CAT rows for different tokens do not collide under `wallet_type='cat'`.
- XCH tier coins need either tagged ownership (`owner_asset_id` / reservation) or a shared XCH planner that serves multiple ladders from one inventory.
- Coin prep becomes a **scheduled shared worker** (queue of per-pair requests), not N independent subprocesses.

---

## Schema / persistence changes

| Store | Change |
|-------|--------|
| `offers` / `fills` / `inventory` / `price_history` | Already have `cat_asset_id` / `asset_id` — keep |
| `coins` | Add `asset_id TEXT` (NULL / `xch` for native); index `(wallet_type, asset_id, status)` |
| `pair_configs` (new) | Persist `PairConfig` overlays keyed by asset |
| `bot_settings` | Stop storing pair economics as flat global keys; migrate to pair-scoped rows |
| `trading_pace` | Add `cat_asset_id` |
| `capacity_reservations` | Add `cat_asset_id` / purpose tags |
| `.env` | Keep process defaults + wallet/Sage settings; live pair overlays live in DB |

---

## Runtime / code changes (high level)

1. Replace `api_server.bot` singleton with `dict[asset_id, PairRuntime]` (a `PairRegistry`).
2. Inject pair identity into the trading loop — **stop ambient reads of `cfg.CAT_ASSET_ID`** inside loop/managers (pass `PairConfig` / `cat_asset_id` explicitly).
3. Keep `cfg` for process-wide settings; pair economics come from `PairConfig`.
4. Serialize wallet mutations (create offer, cancel, split, multi-send) through one lock; share one fee allocator.
5. Per-pair `RiskManager` + optional portfolio XCH exposure cap.
6. Tag SSE/events with `asset_id` so the GUI can filter.
7. Fix `wallet_sage._CAT_ASSET_ID` singleton — every CAT RPC must take explicit asset/wallet id.

Key touchpoints today:

- `src/catalyst/config.py` — `CAT_*`, `XCH_RESERVE`, ladder keys
- `src/catalyst/api_server.py` — `_active_cat`, `bot`, `create_bot()`
- `src/catalyst/blueprints/cat.py` — `api_cat_select` (409 while running)
- `src/catalyst/blueprints/bot.py` — start/stop
- `src/catalyst/bot_loop.py` — `BotLoop`
- `src/catalyst/offer_manager.py`, `coin_manager.py`, `coin_prep_worker.py`
- `src/catalyst/risk_manager.py`, `price_engine.py`, `fill_tracker.py`
- `src/catalyst/wallet_sage.py` — `_CAT_ASSET_ID`
- `src/catalyst/database.py` — schema
- `bot_gui.html` — pair selector UX
- `desktop_app.py` — instance lock / Flask port

---

## API surface (target)

| Endpoint | Behavior |
|----------|----------|
| `GET /api/pairs` | List known pair configs + runtime status |
| `POST /api/pairs` | Add a CAT into the pair list (resolve metadata) |
| `PATCH /api/pairs/<asset_id>` | Update that pair’s config / budget / enabled |
| `DELETE /api/pairs/<asset_id>` | Remove when not running; optional cancel-open |
| `POST /api/pairs/<asset_id>/start` | Start that pair’s loop (budget checks) |
| `POST /api/pairs/<asset_id>/stop` | Stop that pair only |
| `POST /api/bot/start` / `stop` | Optional convenience: start/stop **all enabled** pairs |
| `GET /api/status` | Aggregate + per-pair sections |

Legacy `POST /api/cat/select` remains as “focus pair for UI editing” and does **not** imply exclusive trading once Phase 3 ships.

---

## UI direction

- Replace “one app-wide pair” copy with a **Pairs** panel: list of pairs, each with enable, budget, start/stop, open offers, mid, P&amp;L.
- Dashboard default: aggregate overview; drill into one pair for ladder/settings.
- Smart Settings: run in the context of a selected pair and propose an XCH slice that fits remaining unallocated budget.
- Keep existing charts/session reset behavior when **focus** changes; do not tear down other running pairs.

---

## Phased rollout

### Phase 1 — Pair profiles (no concurrent trading)

Lowest risk; immediate value.

- Persist `PairConfig` per asset in DB.
- On pair focus/switch, load that pair’s economics into the active trading slot (no more leaking SBX spreads onto MZ).
- Still one running loop; still stop-to-switch for trading.
- Delivers remembered setups per CAT.

**First code touchpoints:** new `pair_store.py` + `pair_configs` table; save/load on `api_cat_select`; GUI messaging update; tests that A→B→A restores A’s spreads/tier sizes.

### Phase 2 — Multi-pair visibility + schema prep ✅

- Balances and open-offer counts for multiple CATs on the dashboard (`GET /api/pairs` + Pairs panel).
- Focus pair for controls; background pairs read-only (click to focus when bot stopped).
- Schema: `coins.asset_id` + write-path tagging; offer counts via `count_open_offers_by_cat()`.
- Pair economics remain in `pair_configs` (Phase 1); process-global `bot_settings` unchanged.

### Phase 3 — Concurrent trading (MVP) ✅

- `PairRegistry` hosts up to **4** `BotLoop`s with frozen `PairSnapshot` + `pair_context` overlays.
- `SharedXchLedger` hard-gates per-pair `xch_budget_mojos` (shared wallet capital); buy creates blocked when budget exhausted.
- Process-wide `wallet_op_lock` on mutating Sage RPCs; shared fee pool across pair managers.
- Per-pair start/stop API + Pairs panel controls; incremental start; stop leaves offers resting.
- Focus may change while other pairs keep running so the next pair can be configured/started.

### Phase 4 — Full ops polish

- Allocation-aware Smart Settings.
- Portfolio risk cap and better toxicity isolation.
- SSE namespacing, alerts per pair, richer aggregate P&amp;L.
- Raise pair limit once stable.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Mempool conflicts / double-spend on shared XCH | Single wallet op lock; one fee allocator; no parallel split/create without coordination |
| One pair’s coin prep starves another | Shared prep queue with fair scheduling + per-pair CAT prep; XCH prep planned globally |
| Budget oversubscription | Enforce sum(budgets) ≤ available at enable/start; reject otherwise |
| Thread / resource blowup | Cap concurrent pairs; share watchers where cheap; reuse process health watch |
| Regression on single-pair users | Keep single-pair UX as the default path; multi-pair is additive |
| Wrong-CAT wallet calls | Eliminate module-global CAT asset id; require explicit ids on all CAT RPCs |

---

## Success criteria

1. One CATalyst window can run ≥2 CAT/XCH pairs concurrently against one Sage wallet.
2. Each pair maintains its own ladder, spreads, and risk session.
3. XCH spend never breaches the global reserve or per-pair budgets under normal operation.
4. Stopping pair A does not cancel or disturb pair B.
5. Existing single-pair workflow remains simple (add one pair, start, same mental model).
6. Tests cover: budget enforcement, wallet serialization, pair-scoped offers/cancels, and no cross-pair config bleed.

---

## Product decisions (2026-07-17)

1. **XCH / settings allocation:** Smart Settings proposes per-pair settings and XCH slices (allocation-aware once concurrent trading lands).
2. **Max concurrent pairs:** **4**.
3. **Start model:** Incremental / opt-in. Start one pair, watch how it runs, then start the next when ready. Not “start all at once” as the primary control. (A later convenience “start all enabled” can exist, but the default UX is per-pair start.)
4. **Stopping / disabling a pair that still has live Dexie offers:**  
   **Meaning:** when you stop trading for pair A, its buy/sell offers may still be sitting on the market.  
   **Decision:** leave those offers resting and show a clear banner; require an explicit cancel. Do **not** auto-cancel on stop/disable. (Matches current cancel discipline and avoids surprising the operator.)

---

## Recommended next step

Implement phases in order on this branch:

1. **Phase 1** — persisted pair profiles (remember economics per CAT; still one active loop)
2. **Phase 2** — multi-pair visibility + `coins.asset_id` schema prep
3. **Phase 3** — concurrent loops (up to 4), shared XCH ledger, per-pair start/stop
4. **Phase 4** — allocation-aware Smart Settings + polish
