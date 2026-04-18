# CATalyst Audit Report — Accuracy Review & Corrections

**Companion to:** `docs/CODEBASE_AUDIT_REPORT.md`
**Reviewed:** 2026-04-18
**Method:** Eight parallel Opus-model verification passes, one per section of the original report. Each pass cross-checked specific claims (file sizes, line counts, class/function existence, imports, callers, endpoints, constants, behaviour) against the actual source.
**This document lists ONLY claims that were found to be false, misleading, ambiguous, or nitpicky.** Claims not mentioned here were verified accurate.

---

## Severity legend

| Severity | Meaning |
|----------|---------|
| **false** | The claim is factually wrong and could mislead a reviewer or security auditor into the wrong mental model. Fix before relying on it. |
| **misleading** | The underlying behaviour is real, but the description misframes it, undercounts, conflates, or attributes it to the wrong file/line. |
| **ambiguous** | The claim is defensible on one reading and wrong on another, or omits a load-bearing qualifier. Rewrite for clarity. |
| **minor-nit** | Off-by-a-few line counts, size rounding, small omissions. Not worth acting on individually but collectively indicate the report was LLM-drafted without tight numeric verification. |

---

## A. FALSE claims

These are the priority fixes — the report asserts something the code does not do.

### A1. `offer_manager.py` — `_slot_size_variation` misdescribed
- **Original claim:** "Size jitter. `_slot_size_variation()` adds ±0.5% to each slot; deterministic but undocumented."
- **Reality:** The function (lines 587–607) does not add a ±0.5 % percentage. It adds a small **absolute XCH delta** `step * (slot + 1)` where `step ∈ [1e-8, 1e-5]`, capped at 0.001 XCH, and the delta is **monotonically increasing with slot index and always positive** — not ±. It also has an explicit docstring, so it is **not undocumented**.

### A2. `offer_lifecycle.py` — `REFRESH_POSTED` signal exists
- **Original claim:** "Missing REFRESH_POSTED→OPEN signal. A failed refresh can leave an offer stuck in `refresh_due`."
- **Reality:** `REFRESH_POSTED` is defined as an `OfferSignal` (line 54) and is handled for `REFRESH_DUE` at lines 124–130, transitioning the old offer to `CANCELLED` (semantically correct because the refreshed offer replaces it). The framing "missing signal" is wrong; if there is still a real risk it needs to be re-articulated in terms of `CANCEL_FAILED` paths.

### A3. `fill_tracker.py` — mass-disappearance counter DOES reset
- **Original claim:** "Mass-disappearance counter never resets on good polls — a permanently flaky wallet can 'stick' the counter and treat every diff as a real fill."
- **Reality:** `_mass_disappearance_count` is explicitly reset to 0 on normal polls (line 216 `else: # Normal disappearance — reset counter`), on 3-strike acceptance (line 195), on timeout acceptance (line 204), and on stale-wallet block (line 165). The claimed failure mode is contradicted by the code.

### A4. `coin_prep_worker.py` — fabricated function name
- **Original claim:** Key functions include "`_poll_for_confirmation()`".
- **Reality:** No method `_poll_for_confirmation` exists in the file. Only `_poll_for_coin_count` (line 3824) and `_get_transaction_confirmation_state` (line 606) exist.

### A5. `coin_classifier.py` — wrong caller list
- **Original claim:** "imported by `coin_manager`, `coin_prep_worker`, `database`, `ladder_planner`, `offer_manager`."
- **Reality:** `coin_prep_worker` does **not** import `coin_classifier` (zero grep matches). Actual callers: `coin_manager`, `database` (L821), `ladder_planner` (L164), `offer_manager` (L425), tests.

### A6. `wallet_sage.py` — RPC endpoint names are wrong
- **Original claim:** Endpoints include `split_xch`/`split_cat`, `get_puzzle_hashes`, `delete_offers` (plural).
- **Reality:** Code calls generic `split` (line 1345), not `split_xch`/`split_cat`. Puzzle-hash enumeration endpoint is `get_derivations` (line 3698), not `get_puzzle_hashes`. There is no `delete_offers` (plural) endpoint — `delete_offers_batch()` loops over single `delete_offer` calls.

### A7. `wallet_sage.py` — direct-import caller list
- **Original claim:** "imported via `wallet.py`."
- **Reality:** Directly imported by at least 18 files including `bot_health.py`, `bot_loop.py`, `coin_manager.py`, `api_server.py`, `coin_prep_worker.py`, `sage_node.py`, `fill_tracker.py`, `doctor.py`, and many tests.

### A8. `market_data_collector.py` — line count and source count wrong
- **Original claim:** "~2000+ lines" and "aggregates 6 data sources".
- **Reality:** File is **1778 lines** (off by ~11 %). Module docstring lists 5 sources; with the F78 additions (CoinGecko, Coinset, Dexie trending) the real count is closer to 7–8. "6" is not what the code says.

### A9. `market_data_collector.py` — fabricated function names
- **Original claim:** Key functions include `_fetch_dexie_trades`, `_fetch_dexie_ticker`, `_fetch_spacescan_token_info`, `_fetch_internal_db_metrics`, `_compute_volatility`, `_compute_liquidity_rating`, `_compute_fill_rate_context`, `_recommend_spread`.
- **Reality:** **None of those names exist.** Actual names are `_fetch_dexie_trade_history` (L295), `_fetch_dexie_ticker_extended` (L548), `_fetch_spacescan_data` (L954), `_fetch_internal_db_history` (L1146), `_analyze_volatility` (L1325), `_analyze_liquidity` (L1491), `_analyze_token_health` (L1558), `_analyze_bot_performance` (L1619). `_compute_fill_rate_context` and `_recommend_spread` are entirely fabricated.

### A10. `spacescan.py` — free-tier budget is daily, not monthly
- **Original claim:** "Free-tier 30 calls/month" (stated twice in the report).
- **Reality:** `_FREE_DAILY_BUDGET = 30  # ~1000/month, leave headroom` (L46). The 30-call budget is **daily**; the monthly figure is ~1000, not 30.

### A11. `mempool_watcher.py` — mislabelled hashing concept
- **Original claim:** "The Dexie mapping coin encoding via sha256(parent_coin_info + puzzle_hash + amount_bytes)".
- **Reality:** That formula is the **Chia coin-ID** hash in `mempool_watcher.compute_coin_id` (L68–77). It has nothing to do with Dexie mapping. Dexie's `_fingerprint` is a separate SHA256 over the offer bech32 and lives in `dexie_manager.py`.

### A12. `market_intel.py` — `BOT_TAG` is not used here
- **Original claim:** "own-offer identification fragile when `cfg.BOT_TAG` blank".
- **Reality:** `BOT_TAG` does not appear in `market_intel.py` (zero grep hits). Whatever own-offer mechanism exists in this file, it is not `BOT_TAG`-based.

### A13. `bot_health.py` — function list and size all wrong
- **Original claim:** Size "~22KB, ~582 lines"; key functions "`run_runtime_checks` (if present), plus helpers for wallet sync meta, offer accounting, coin status, performance metrics"; callers "`config`, `database`, `offer_manager` (conditional)".
- **Reality:** Size is 26.5 KB / 684 lines. Real top-level functions are `check_pending_cancels` (L146), `check_orphan_locks` (L371), `check_stale_dexie_posts` (L472), `check_ladder_overbuild` (L560), `run_runtime_checks` (L658). None of the "wallet sync meta / offer accounting / coin status / performance metrics" helpers exist. `offer_manager` is **never** imported (zero grep hits); `super_log` is a top-level import and was omitted.

### A14. `ladder_planner.py` — "consumed by offer_manager" is wrong
- **Original claim:** "consumed by `offer_manager`, potentially `bot_loop`".
- **Reality:** Neither `offer_manager` nor `bot_loop` imports `ladder_planner`. Real callers: **tests only** (`tests/test_ladder_planner.py`), plus a passing comment in `config.py:472`.

### A15. `database.py` — line count off by ~26 %
- **Original claim:** "~3461 lines".
- **Reality:** **4358 lines**. Off by ~900 lines.

### A16. `event_taxonomy.py` — map entry count is grossly stale
- **Original claim:** "~168 event types into 8 categories" (also in the module docstring).
- **Reality:** `_EVENT_CATEGORY_MAP` contains **516 entries** (runtime `len()`). The 8-category count is correct. The "168" figure is stale — the map has tripled without the docstring being updated. The report inherited the stale number.

### A17. `api_server.py` — `/api/log` is NOT token-exempt
- **Original claim:** "token-exempt endpoints (`/api/splash/incoming`, `/api/log`)" and "`POST /api/log` (token-exempt bulk flush)".
- **Reality:** Only `/api/splash/incoming` is in `_TOKEN_EXEMPT_WRITE_ROUTES` (L148–150). `/api/log` is in `_RATE_LIMIT_EXEMPT_WRITE_ROUTES` (L154–157) and **still requires the local token** via the `before_request` hook. The report conflates rate-limit-exemption with token-exemption — a material security-relevant error.

### A18. `catalyst.spec` — `.env.example` is NOT bundled
- **Original claim:** "datas include `bot_gui.html`, `assets/`, `.env.example`".
- **Reality:** `.env.example` is deliberately not bundled. Spec comment (L21) says ".env is never bundled — it lives alongside the exe and holds secrets." Real datas: `bot_gui.html`, `splash.html`, assets, `splash.exe`, `coin_prep_worker.py`.

### A19. `win_subprocess.py` — STARTUPINFO claim is nonsensical
- **Original claim:** "bitwise-or on flags without validating caller-provided STARTUPINFO".
- **Reality:** The function accepts no `STARTUPINFO` parameter (signature is `hidden_subprocess_kwargs(detached=False, new_process_group=False)`). It constructs its own internally. There is no caller-provided STARTUPINFO to validate.

---

## B. MISLEADING claims

The underlying observation is real but the description misframes it.

### B1. `bot_loop.py` — `stop()` join timeout
- **Claim:** "`stop()` uses a 10s join timeout".
- **Reality:** Main cycle thread uses `join(timeout=30)` (L2279). The 10 s is the timeout for the background watcher threads (L2292). `splash_receive_thread` uses 5 s (L2282). The 10 s figure was a misattribution.

### B2. `bot_loop.py` — caller list error
- **Claim:** "Modules/callers that import it: `api_server`, `database` (indirect), `super_log_hooks`."
- **Reality:** `database.py` does **not** import `bot_loop`. `risk_manager.py` (L1011) does, and was omitted.

### B3. `bot_loop.py` — 3-strike line reference is wrong file
- **Claim:** "Fill-detection 3-strike rule (~line 108) trusts wallet RPC consistency." (cited under bot_loop)
- **Reality:** That rule lives in `fill_tracker.py`, not `bot_loop.py`. `bot_loop.py:108` is unrelated module-level code.

### B4. `fill_classifier.py` — caller list
- **Claim:** "Modules/callers: `bot_loop` (via `splash_receive`), `fill_tracker`, `sweep_coordinator`."
- **Reality:** Direct callers include `api_server` (L4098), `bot_loop` (L3550, **direct** — not via splash_receive), `fill_tracker` (L1098), `sweep_coordinator` (L223). The "via splash_receive" is unsupported; `api_server` was missed.

### B5. `coin_prep_worker.py` — import list
- **Claim:** "Imports it depends on: `wallet`, `tx_fees`, `coin_prep_utils`, `database`."
- **Reality:** `database` is only lazy-imported inside functions. Top-level imports include `wallet`, `coin_prep_utils`, `tx_fees`, `win_subprocess`, `dotenv`. `win_subprocess` was omitted.

### B6. `reservation_manager.py` — caller list incomplete
- **Claim:** "`api_server`, `bot_loop`, `offer_manager` (lazy)".
- **Reality:** Also imported by `coin_manager` (L3131, lazy) and `database` (L545).

### B7. `coin_reservations.py` — owner-collision framing
- **Claim:** "owner-string collisions are not enforced (risk of one owner releasing another's coins)".
- **Reality:** `release()` (L160) explicitly checks `r.owner == owner` before deleting. The actual risk is **two callers accidentally using the same owner string**; the wording "one owner releasing another's" misdescribes the mechanism.

### B8. `coin_prep_utils.py` — "hardcoded" misapplied
- **Claim:** "Hardcoded 90% completion threshold; max retries fixed at 1".
- **Reality:** `min_completion_ratio: float = 0.90` (L44) and `max_retries: int = 1` (L13) are **defaults of keyword arguments** that callers can override. They are not hardcoded constants.

### B9. `wallet_chia.py` — "imported only via wallet.py"
- **Claim:** "imported only via `wallet.py`".
- **Reality:** Also imported directly by `api_server.py`, `doctor.py`, and `tests/test_all_apis.py`.

### B10. `wallet_sage.py` — `get_all_offers` filter framing
- **Claim:** "**`get_all_offers` client-side drops completed** — history-dependent code loses data."
- **Reality:** Default is `include_completed=True` — nothing is dropped by default. The client-side filter only runs when callers explicitly pass `include_completed=False`. Filtering is opt-in, not default lossy.

### B11. `wallet_sage.py` — `cancel_offer` and `SageAlreadyIncluding`
- **Claim:** "`cancel_offer` (V5 FIX: treats 404 as success; **handles `SageAlreadyIncluding`**)".
- **Reality:** `cancel_offer` (L2322) does treat 404 / "Missing offer" / "not found" as success, but there is no explicit `except SageAlreadyIncluding`. That specific handling exists only in `cancel_offers_batch` (L3086).

### B12. `wallet_sage.py` — `get_wallet_balance` "owned count"
- **Claim:** "uses `selectable_balance` for spendable, **owned count** for total".
- **Reality:** Total is the **sum of owned coin amounts**, not the **count** (lines 1673, 1718).

### B13. `wallet_sage.py` — fingerprint mismatch "error swallowed"
- **Claim:** "Fingerprint mismatch detected AFTER login succeeds; error swallowed if super_log missing".
- **Reality:** On mismatch, the function always prints the error and returns `False` (L646–657). Only the `log_event` side effect is swallowed when super_log is unavailable. The mismatch result (refuse to start) is **not** swallowed.

### B14. `market_data_collector.py` — state description
- **Claim:** "per-source caches".
- **Reality:** All caching is DB-backed via `get_market_analysis_cache`/`set_market_analysis_cache`. No instance-level per-source caches exist — only `_session`.

### B15. `market_intel.py` — DBX threshold hardcoded claim
- **Claim:** "hardcoded DBX threshold (500 bps)".
- **Reality:** Threshold is read as `getattr(cfg, "DBX_MAX_SPREAD_BPS", Decimal("500"))` (L91, L506) — 500 is only the default, not hardcoded. (Whale threshold 1 XCH is genuinely hardcoded.)

### B16. `amm_monitor.py` — requote latency
- **Claim:** "requotes fresh within ~60 s on AMM drift".
- **Reality:** Default `AMM_POLL_INTERVAL_SECS` is 30 s (L322). Module docstring says "within one poll interval (default 30s)". ~60 s is roughly 2× the real figure.

### B17. `spacescan.py` — `market_data_collector` as "consumer"
- **Claim:** spacescan is "consumed by `market_data_collector`".
- **Reality:** `market_data_collector` only imports `spacescan` for call-counting (L884) and has its own `_spacescan_smart_get` helper. None of the listed spacescan "key functions" (is_coin_spent, verify_fill, get_xch_balance, etc.) are consumed by it.

### B18. `bot_health.py` — "superseded by RuntimeMonitor"
- **Claim:** "largely superseded by RuntimeMonitor".
- **Reality:** bot_health's docstring positions it as the active-repair sister of the passive watchdog `runtime_monitor`. They are complementary, not overlapping — bot_health does auto-repair (pending-cancel cleanup, orphan-lock release, stale Dexie repost, ladder overbuild correction); RuntimeMonitor only emits derived warnings. "Superseded" is unsupported.

### B19. `risk_manager.py`, `sniper.py`, `boost_manager.py` — "conditional import" is DI
- **Claim (risk_manager):** "conditionally `bot_loop`, `dexie_manager`". **(sniper):** "optionally `risk_manager`, `dexie_manager`, `splash_manager`". **(boost_manager):** "optionally `risk_manager`, `dexie_manager`".
- **Reality:** In all three files those modules are **constructor-injected** (passed as args and stored on `self`), not imported. `risk_manager.py` has exactly one lazy `bot_loop` import at L1011; `dexie_manager` is accessed via `getattr(self, "_dexie_manager", None)`. Calling DI "conditional import" is a category error.

### B20. `database.py` — `trading_pace` table missing from enumeration
- **Claim:** Tables listed: offers, fills, coins, inventory, price_history, events, config_history, bot_settings, splash_incoming_offers, pool_snapshots, market_analysis_cache, reservation_leases.
- **Reality:** `trading_pace` (L424, `CREATE TABLE IF NOT EXISTS trading_pace`) is also created in `database.py` and was omitted.

### B21. `super_log.py` — "~95 % reduction" is unsubstantiated
- **Claim:** "~95 % reduction in disk volume while preserving crash forensics".
- **Reality:** No grep hit for `95` / `reduction` / any supporting metric in super_log.py or its tests. The figure reads as marketing copy with no source.

### B22. `app_bridge.py` — method count
- **Claim:** "~82 methods" / "82+ methods are unauthenticated".
- **Reality:** 91 `@_safe`-decorated methods at `AppBridge` class scope (93 total `def` minus `__init__` and the `api` property). Report's own enumerated list sums to ~90 names. "82" undercounts by ~10.

### B23. `app_bridge.py` — `restart_sage` is a stub
- **Claim:** `restart_sage` listed as a bridge capability under "Wallet / CAT".
- **Reality:** Method exists (L872) but unconditionally returns `{"success": False, "message": "Sage must be restarted manually..."}` (L873–877). Listing it as a capability without noting it is a no-op is misleading.

### B24. `.github/workflows/build-release.yml` — macOS artifact
- **Claim:** "package (.zip / Inno Setup .exe / .app / tar.gz)".
- **Reality:** macOS does **not** produce a `.app` as the final artifact — it zips the `.app` bundle into a `.zip` (L100–103 `zip -r "...-${{ matrix.ext }}" CATalyst.app/` with `ext: .zip`). Windows produces **both** a `.zip` and an Inno Setup `.exe`, not one or the other.

### B25. `cat_resolver.py` — "never overwrites"
- **Claim:** "Never overwrites existing `.env` values."
- **Reality:** Overwrites `CAT_NAME` when its current value is the generic default `"MZ"` (L184–186). A user with `CAT_NAME=MZ` will have it silently replaced.

### B26. `splash_setup.py` — SHA256 is conditional
- **Claim:** "Mandatory SHA256 — no fallback on verify failure".
- **Reality:** SHA256 verification only runs if the GitHub release has a `.sha256` sidecar asset (L188–195, L242 `if sha256_url:`). If no sidecar is present, the binary is installed with **no integrity check at all**. "Mandatory" is conditional on release-side provisioning.

---

## C. AMBIGUOUS claims

Defensible on one reading but misleading on another.

### C1. `fill_classifier.py` — config puzzle-hash dedupe framing
- **Claim:** "Config puzzle-hash dedupe is silent — typos in config never get detected."
- **Reality:** Code builds a `set()` with case-normalisation and `0x` stripping. **Equivalent** hashes are silently deduped. Typos (malformed hashes) are kept as distinct but ineffective entries. The risk wording conflates two different failure modes.

### C2. `coin_prep_worker.py` — grace-extension spiral
- **Claim:** "up to 2 extensions +60 s each".
- **Reality:** `should_extend_pending_consumed_split_grace` in `coin_prep_utils.py` returns `False` when `extensions_used >= 1` (L57), so only **1** extension via that helper. A separate retry branch in the worker could plausibly add a second +60 s bump, so "up to 2" is reachable in theory, but via the named helper alone the limit is 1.

### C3. `dexie_manager.py` — endpoint grouping
- **Claim (Section 4 preamble):** "`/v3/prices/historical_trades`, `/pairs`, `/quote`".
- **Reality:** Names are individually correct but the grouping mixes Dexie (`/v3/prices/historical_trades`, `/v3/prices/pairs`) with TibetSwap (`/pairs`, `/quote`) without labelling ownership.

### C4. `market_data_collector.py` — cache TTLs
- **Claim (Section 4 preamble):** "5min/30min/1440min for market_data_collector".
- **Reality:** The module has `CACHE_TTL_TRADES = 60` min (L51), `CACHE_TTL_ANALYSIS = 30` min (L55), `CACHE_TTL_TIBET = 30`, and others. The Section-4 summary is imprecise about which TTL belongs to which source.

### C5. `price_engine.py` — `_decimal_sqrt` listing
- **Claim:** Listed among `PriceEngine` key functions.
- **Reality:** Module-level function at L931, not a method. Presentation implies it is a `PriceEngine` member.

### C6. `price_engine.py` — "consumed by" vs DI
- **Claim:** "consumed by `bot_loop`, `risk_manager`, `amm_monitor`, `super_log_hooks`".
- **Reality:** `risk_manager` and `amm_monitor` receive it via constructor injection, never importing it at module scope. Technically "consumed", but inconsistent framing with other sections.

### C7. `shape_fix_orchestrator.py` — "one flow per side globally"
- **Claim:** "one flow per side globally".
- **Reality:** Module docstring (L23–26) and code (L198–199) say **max one flow anywhere** — globally serialised across both sides. The report's phrasing reads as "one per side", which is the opposite of the actual max-one-across-both-sides semantics.

### C8. `user_secrets.py` — "only SPACESCAN_API_KEY hard-wired"
- **Claim:** "only SPACESCAN_API_KEY hard-wired".
- **Reality:** Opus agent did not find a direct `SPACESCAN` reference in `user_secrets.py`. The `apply_to_config` path may hard-code it elsewhere; flagged for re-check.

### C9. `api_server.py` — `/api/splash/receive` as two routes
- **Claim:** Listed as `GET /api/splash/receive` and `POST /api/splash/receive`.
- **Reality:** Single decorator `@app.route("/api/splash/receive", methods=["GET", "POST"])` (L5588). One route, two methods. Affects the "~120 endpoints" headline count.

### C10. `.github/workflows/code-quality.yml` — vulture step is non-blocking
- **Claim:** "lint-and-syntax (AST parse + import check + `vulture --min-confidence 90`)".
- **Reality:** The vulture command is suffixed with `|| true` (L64) — findings never fail CI. Presenting it as an enforced gate overstates its effect.

---

## D. MINOR-NITS

Off-by-a-few lines, size rounding, small omissions. Listed for completeness.

| File | Claim | Actual |
|------|-------|--------|
| `bot_loop.py` | ~8985 lines | 9004 |
| `coin_prep_worker.py` | ~285 KB | 291 KB |
| `price_engine.py` | ~944 lines | 943 |
| `dexie_manager.py` | ~719 lines | 718 |
| `dexie_manager.py` | "parallel ≥10 batch" | actually `len(batch) > 10` |
| `market_intel.py` | ~603 lines | 602 |
| `spacescan.py` | ~685 lines | 684 |
| `amm_monitor.py` | ~22 KB / ~510 lines | ~21 KB / 509 |
| `mempool_watcher.py` | ~568 lines | 567 |
| `dynamic_amm_buffer.py` | ~6.8 KB / ~189 lines | ~6.9 KB / 188 |
| `reaction_strategy.py` | "~1.3KB payload" | actual 5.78 KB |
| `ladder_planner.py` | ~6.5 KB | 12.7 KB |
| `ladder_watchdog.py` | ~11 KB | 19.5 KB |
| `config.py` | "~120 settings" referenced in scan brief | 216 UPPERCASE settings on `cfg` |
| `config.py` | ~1117 lines | 1116 |
| `super_log.py` | ~933 lines | 935 |
| `event_taxonomy.py` | ~545 lines | 586 |
| `super_log_hooks.py` | "~60+ wrappers" | ~80 (undercount) |
| `api_server.py` | "~120 endpoints" / "~573 KB" | 126 `@app.route` / 586 KB |
| `api_server.py` | "Rate limit 20 req/10s" | 21st request rejected (off-by-one) |
| `api_server.py` | "200/s splash" | 200th request rejected (off-by-one) |
| `app_bridge.py` | ~51 KB | 50 KB |
| `tray_manager.py` | ~13 KB | 12 KB |
| `desktop_app.py` | key functions list puts nested `on_closing` at module scope | nested inside `run_desktop_mode` |
| `wallet_sage.py` | `_wallet_id_to_asset_id` listed among functions | it's a module-level dict (L145), not a function |
| `wallet.py` | symbol list | omits re-exported constants (`WALLET_ID_XCH`, `WALLET_URL`, `CERT_PATH`, `KEY_PATH`, `HEADERS`, `WALLET_DEBUG`, Chia-only `FULL_NODE_URL`/`CERT`/`KEY`) and local `get_owned_coins_detailed` shim (L90) |
| `mempool_watcher.py` | "MIN_SIGNAL_MAGNITUDE = 0.05 %" | constant is unitless `0.05` |
| `market_intel.py` | poll intervals | omits `_dbx_check_interval = 300` (5 min) |
| `dexie_manager.py` | "module-level `_offer_detail_cache` (15s)" | 15 s is a default argument to `get_offer_detail`, not a fixed module TTL |
| `amm_monitor.py` | "AMM drift threshold 40 BPS" | configurable default, not hardcoded |
| `coin_classifier.py` → `coin_fsm.py` | private `_expand()` listed as key helper | module-level import-time builder; not a callable API |
| `coin_manager.py` | `_classify_coins` grouped with class methods | actually module-level (L309) |
| `fill_tracker.py` | callers | omits `super_log_hooks.py:172` |
| `reaction_strategy.py` | "potentially offer_manager" | offer_manager does import it at top level — not "potentially" |
| `code-quality.yml` | ".gitignore patterns" | omits `*.crt` |
| `tests/` catalog | 65 test files | 65 (correct total), but `tests/test_reservation_manager.py` is not enumerated in any bullet |

---

## E. Summary stats

| Severity | Count | Action |
|----------|------:|--------|
| **false** | 19 | Fix the narrative — these are the items a security reviewer would otherwise rely on incorrectly |
| **misleading** | 26 | Rewrite with accurate framing |
| **ambiguous** | 10 | Add qualifiers or rewrite |
| **minor-nit** | ~35 | Batch-update sizes / line counts; low priority individually |

The consistent thread across A and B findings is that **numeric claims and caller lists are the least reliable parts of the original report**. Behavioural risks that were verified tend to hold up (SSL off, no exponential backoff, watch-only guard, bridge bypass, Spacescan rate limits, cert validity, tier enforcement, etc.). But anywhere the report counted something (methods, routes, lines, tables, cache TTLs), there's a reasonable chance the number is stale or simply wrong.

**Highest-impact fixes to make to the original report:**

1. A17 — `/api/log` is not token-exempt. Correct this before the report informs any security review.
2. A2, A3 — remove the claimed "missing signal" and "counter never resets" risks; they are contradicted by the code.
3. A9, A13 — regenerate the function lists for `market_data_collector.py` and `bot_health.py` from source; the current lists are largely fabricated.
4. A18 — correct the `.env.example` bundling claim; the spec actively documents the opposite.
5. A14 — `ladder_planner.py` has no production callers; describing it as consumed by `offer_manager` misrepresents its role (it's currently only test-exercised).
6. A16 — update the event-taxonomy count (168 → 516) and the stale docstring in `event_taxonomy.py` itself.

---

*End of corrections document.*
