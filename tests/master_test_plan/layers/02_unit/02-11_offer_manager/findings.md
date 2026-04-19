# Findings — Slice 02-11

Unit tests for `offer_manager.py` — offer lifecycle manager.

---

## Existing coverage (before this slice)

None — no tests directly exercised OfferManager helpers.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `xch_to_mojos` / `mojos_to_xch` | 5 | 1 XCH, fractional, truncation, roundtrip, zero |
| `cat_to_mojos` / `mojos_to_cat` | 5 | 3 decimals, 0 decimals, truncation, roundtrip, 12 decimals |
| `CANCEL_PENDING_METHODS` | 3 | membership checks |
| `_slot_size_variation` | 5 | positive, monotone, never exceeds cap, negative clamped, adaptive step |
| `_size_key` | 2 | 8dp normalisation, float input |
| `_coin_designation_priority` | 6 | preferred/no-preferred combos, unknown |
| Slot suspension lifecycle | 8 | threshold, below threshold, clear, count, cross-side isolation, auto-clear |
| Bot-cancel tracking | 5 | not-cancelled, add, non-destructive read, cache miss, cache hit |
| `detect_expiring_offers` | 7 | empty, soon, far, expired, no valid_times, zero, custom window |
| `_classify_tier` | 7 | disabled, zero total, buy inner/mid/outer, ratio fallback inner/mid |
| `should_requote` | 6 | disabled, cooldown, zero price, small drift, large drift, per-side cooldown |
| `_allocate_unique_requested_mojos` | 4 | no collision, collision, adds to used, multiple unique |

**63 new tests** in `tests/test_plan_02_11_offer_manager_unit.py`.

---

## Test corrections

- `test_xch_to_mojos_truncates_not_rounds`: Initially used `0.0000000001 XCH`
  which equals 100 mojos (not 0). Corrected to `0.0000000001 * 0.001 = 1e-13 XCH`
  which gives 0.1 mojos → truncated to 0.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
