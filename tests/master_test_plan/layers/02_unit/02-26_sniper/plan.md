# Slice 02-26: sniper.py unit tests

**Layer:** 2 · **Estimated time:** 45 min · **Escalate to Opus if:** the
single-sided gate interacts unexpectedly with `try_snipe_single` callers.

## Goal

Comprehensively unit-test `sniper.py` — probe sizing, cooldown, caps,
the liquidity-mode gate (added 2026-04-19), and coin selection.

## Scope

### In-scope
- `Sniper.__init__`, state initialisation
- `Sniper.try_snipe(bid, ask, arb_gap_bps)` — both-sides probe
- `Sniper.try_snipe_single(side, price, arb_gap_bps)` — one-side probe
- `Sniper._calculate_snipe_size`
- `Sniper._should_snipe_side`
- `Sniper.prune_active_snipes`
- `Sniper.get_stats`
- The `_mode` gate guarding both try_* methods

### Out-of-scope
- `_create_snipe_offer` — already tested in `test_sniper_coin_ids.py`
- `_publish_immediately` network calls — stub

## Checks

### 1. Liquidity-mode gate (2026-04-19 behaviour)
- [ ] **1.1** `try_snipe()` with cfg.LIQUIDITY_MODE='buy_only' returns `[]` BEFORE cooldown check fires
- [ ] **1.2** Same for 'sell_only'
- [ ] **1.3** 'two_sided' doesn't short-circuit
- [ ] **1.4** `try_snipe_single()` mirrors the gate
- [ ] **1.5** Gate reads cfg LIVE, not cached at init — changing mode mid-session takes effect

### 2. Cooldown
- [ ] **2.1** After a successful snipe, try_snipe returns [] until SNIPER_COOLDOWN_SECS elapses
- [ ] **2.2** Cooldown of 0 allows back-to-back snipes (respects cap)

### 3. Cap
- [ ] **3.1** `len(_active_snipe_ids) >= _max_active_snipes` blocks new probes
- [ ] **3.2** After `prune_active_snipes(fresh_ids)`, a filled/cancelled snipe is removed and new probes allowed

### 4. Size calculation
- [ ] **4.1** `_calculate_snipe_size(arb_gap_bps)` returns `SNIPER_SIZE_XCH` for normal gaps
- [ ] **4.2** (Verify the actual scaling behaviour — read the source; if no scaling, say so)

### 5. Side enablement
- [ ] **5.1** `_should_snipe_side("buy")` when `cfg.ENABLE_BUY=False` returns False
- [ ] **5.2** `_should_snipe_side("sell")` when circuit breaker side_long_halt is set — returns False
- [ ] **5.3** No risk_manager attached → returns True by default

### 6. try_snipe happy path (with stubs)
- [ ] **6.1** Given two valid prices + stubbed offer_manager, returns list of created offers
- [ ] **6.2** Both-sided: creates two offers (buy + sell)
- [ ] **6.3** If one side creation fails, the other still goes through
- [ ] **6.4** `_last_snipe_time` is updated

### 7. try_snipe_single happy path
- [ ] **7.1** Creates one offer on the requested side
- [ ] **7.2** Posts to dexie_manager FIRST, then splash_manager (publish ordering)
- [ ] **7.3** Posting failure doesn't break the return value

### 8. Invalid inputs
- [ ] **8.1** try_snipe with `bid<=0` returns []
- [ ] **8.2** try_snipe with `ask<=0` returns []
- [ ] **8.3** try_snipe_single with unknown side ("up") returns []

### 9. Stats
- [ ] **9.1** `get_stats()` returns the documented fields (total_snipes, active_snipes, cooldown_secs, etc.)
- [ ] **9.2** `recent_snipes` is capped at `_max_history`

## Execution notes

Existing tests live in `test_sniper_coin_ids.py` (3 cases). Add new tests
to `test_sniper_unit.py` (create if needed). Use the same _FakeCfg
pattern but remember the hermetic-test rules from
`test_liquidity_mode.py` (don't `del sys.modules['config']` — mutate
the already-imported cfg singleton).

## Success criteria

- 25+ new pytest cases in `test_sniper_unit.py`
- Original 3 `test_sniper_coin_ids.py` cases still pass (no regressions)
- All liquidity-mode gate behaviour documented in tests so a future F79-
  style accidental inversion is caught immediately
