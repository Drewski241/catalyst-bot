# Findings — Slice 03-17

Integration tests for `CoinManager.needs_topup()` trigger conditions and
`_record_topup_pool_spend()` DB persistence.  No wallet calls — tests use
a temp SQLite DB and patched cfg.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestNeedsTopupGates` | 5 | topup_running / prep_running / both-cooldowns / drip-override / zero-time |
| `TestNeedsTopupThreshold` | 7 | zero XCH/CAT, healthy coins, buy/sell-only mode, threshold scales with MAX_ACTIVE |
| `TestTopupPoolSpendPersistence` | 5 | zero noop, XCH spend, CAT spend, accumulation, independence |
| `TestTopupCooldownState` | 3 | backoff flag, last_topup_time=0, topup/prep running=False |

**19 new tests** in `tests/test_plan_03_17_topup_worker_integration.py`.

## No bugs found

All 19 tests passed (after one fix: `init_db()` → `init_database()`).

## Scope

Tests cover the non-tiered path (`TIER_ENABLED=False`) of `needs_topup()`.
The tiered path (TIER_ENABLED=True) requires more cfg fields and would need
integration with live tier distribution — deferred to Layer 6 (live-fire).

## Key isolation technique

`cfg.WALLET_FINGERPRINT = "12345678"` prevents `_resolve_fingerprint()` from
making wallet RPC calls during `CoinManager.__init__`.
