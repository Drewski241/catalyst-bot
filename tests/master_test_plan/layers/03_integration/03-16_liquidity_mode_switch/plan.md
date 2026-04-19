# Slice 03-16: liquidity-mode switch cycle

**Layer:** 3 · **Estimated time:** 50 min · **Escalate to Opus if:** any
side-effect lingers across the cycle (dust coins, orphan offers, stale
status flags) and the fix needs multi-module reasoning.

## Goal

End-to-end integration test: user starts in two_sided, switches to
buy_only, runs coin prep, verifies bot actually honours the mode, then
flips back. Confirms no state leaks between modes and no offers on the
"wrong" side persist.

## Scope

### In-scope
- `config.LIQUIDITY_MODE` round-trip via `/api/settings`
- `/api/smart-defaults?liquidity_mode=...` response shape
- `/api/coin-prep/trigger` side-specific pool build
- `/api/status` `liquidity` block updates correctly
- Bot-loop gate: with buy_only, no sell offers created
- Sniper gate: in single-sided, no probes even on arb gap

### Out-of-scope
- UI rendering of the picker (that's slice 05-07)
- Actual on-chain coin splits (use DRY_RUN or a mocked wallet)

## Checks

### 1. Setup
- [ ] **1.1** Bot stopped. `LIQUIDITY_MODE=two_sided` in env. Confirm via `/api/config`.
- [ ] **1.2** Wallet has balanced XCH + CAT (test-wallet state or mocked).

### 2. Switch to buy_only
- [ ] **2.1** POST to `/api/settings` body `{"liquidity_mode": "buy_only"}`
- [ ] **2.2** GET `/api/config` → `LIQUIDITY_MODE=buy_only`, `ENABLE_BUY=True`, `ENABLE_SELL=False`
- [ ] **2.3** GET `/api/status` `liquidity` block → `mode=buy_only`, `active_side=buy`
- [ ] **2.4** GET `/api/smart-defaults?liquidity_mode=buy_only&...` returns expected zeros
  - `max_active_sell == 0`
  - all `sell_*_size_xch == None`
  - `sniper_enabled == False`
  - `topup_pool_cat == 0`

### 3. Coin prep under buy_only
- [ ] **3.1** POST `/api/coin-prep/trigger` with `{coin_multiplier: 1.0, full_reset: false}`
- [ ] **3.2** Wait for completion via `/api/coin-prep/status` (poll)
- [ ] **3.3** Inspect the worker's CLI args (logs or mock capture): `cat_tier_counts` should all be 0
- [ ] **3.4** Post-prep coin inventory: `cat_trading` coin count is 0 (or ≤ some tiny number from dust)
- [ ] **3.5** Fee pool still built (XCH side always needs fees)
- [ ] **3.6** Sniper pool is 0 (not prepped)

### 4. Start bot in buy_only
- [ ] **4.1** POST `/api/bot/start` in dry-run mode
- [ ] **4.2** Wait for cycle 1 complete
- [ ] **4.3** `/api/offers` lists only buy offers, `wallet_sell == 0`
- [ ] **4.4** No sniper offers placed on a 10%+ arb gap (simulate via price_engine mock if feasible)

### 5. Flip to sell_only mid-stop
- [ ] **5.1** POST `/api/bot/stop`, wait for all offers cancelled
- [ ] **5.2** POST `/api/settings` body `{"liquidity_mode": "sell_only"}`
- [ ] **5.3** `/api/config` confirms `LIQUIDITY_MODE=sell_only`, `ENABLE_BUY=False`, `ENABLE_SELL=True`
- [ ] **5.4** `/api/status.liquidity.mode == "sell_only"`
- [ ] **5.5** Mode-switch while bot is RUNNING is refused (write returns an error or the field is ignored)

### 6. Coin prep + start under sell_only
- [ ] **6.1** Coin prep: xch_trading 0, cat_trading non-zero, fee pool still built
- [ ] **6.2** Bot-start: only sell offers placed
- [ ] **6.3** Reverse Buy Ladder flag has no effect (buy ladder is off)

### 7. Return to two_sided
- [ ] **7.1** Stop bot, switch mode, coin prep, start
- [ ] **7.2** Both sides quote
- [ ] **7.3** Sniper re-enables if SNIPER_ENABLED=True in cfg (sanity check)

### 8. State hygiene
- [ ] **8.1** No orphan offers left in wallet from previous modes
- [ ] **8.2** No orphan coin-lock rows in DB `coins` table
- [ ] **8.3** Fills table preserved (default preserve_history path)
- [ ] **8.4** Runtime stats not reset (session count ≥ previous)

## Execution notes

Set up a pytest fixture that:
- Spawns the Flask server in --flask mode in a subprocess on a free port
- Uses a mocked wallet module (can't hit live Sage from tests)
- Tears down offers / coins between checks

Or — if that's too heavy for now — execute the checks against the
running dev instance manually, documenting each `/api/*` response in
findings.md.

## Success criteria

- Mode round-trip (two→buy→sell→two) leaves no residual state
- All three modes' coin prep produces the expected pool shape
- Bot never places an offer on a disabled side, even under arb-gap
  pressure
- Any "leak" (orphan offer, stale counter) is filed as a finding and
  either fixed or escalated to Opus
