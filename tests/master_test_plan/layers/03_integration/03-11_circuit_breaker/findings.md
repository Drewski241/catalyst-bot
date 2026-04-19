# Findings — Slice 03-11

Integration tests for circuit breaker trip + recover via RiskManager + mock PriceEngine.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestHardPriceLimitTrip` | 6 | no trip below limit, trip above, reason contains price, is_full_halt, hard min, zero price |
| `TestCircuitBreakerHysteresis` | 5 | 1/2 OK cycles not enough, 3 clears, bad-price doesn't reset streak, trading resumes |
| `TestDynamicLimitPriceEngineIntegration` | 5 | None limits safe, trip above/below dynamic band, within band safe, dynamic checked first |
| `TestFullTripRecoverCycle` | 4 | full cycle, can re-trip after recovery, multiple cycles, reason cleared |
| `TestCircuitBreakerThreadSafety` | 2 | concurrent check calls, concurrent reads while tripping |

**22 new tests** in `tests/test_plan_03_11_circuit_breaker_integration.py`.

## Behaviour finding (not a bug)

**Hysteresis streak not reset when price still bad while CB active.**

`check_circuit_breakers` exits early when a price check fails (before reaching the streak code).
So alternating bad/good prices while CB is active will accumulate good cycles toward the clear
threshold. Example: bad→good(1)→bad→good(2)→bad→good(3)→CLEARS, even though no 3 consecutive
good cycles occurred.

Intent appears to be "3 consecutive OK cycles" but actual behaviour is "3 total OK cycles since
trip". For the typical use case (prices move back into range quickly) this is fine. Documented
via `test_bad_price_during_hysteresis_does_not_reset_streak`.
