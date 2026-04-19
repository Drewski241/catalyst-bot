# Findings — Slice 02-16

Unit test expansion for `coin_classifier.py` — pure classification module.

---

## Existing coverage (before this slice)

None — no tests referenced coin_classifier.py directly.

---

## New coverage added

| Function | Tests | Notes |
|----------|-------|-------|
| `classify_coin` — edge cases | 4 | Zero, negative, empty tiers, all-zero tiers |
| `classify_coin` — DUST | 3 | Below threshold, at threshold, nearest_tier=smallest |
| `classify_coin` — RESERVE | 3 | At threshold, below threshold, nearest_tier=largest |
| `classify_coin` — EXACT | 4 | Inner exact, mid exact, at floor |
| `classify_coin` — OVERSIZE_FIT | 2 | Slightly over tier size, at ceiling |
| `classify_coin` — MISFIT | 3 | Between tiers, just below floor, candidates populated |
| `classify_coin` — best_tier preference | 2 | EXACT beats OVERSIZE, smallest EXACT chosen |
| `is_misfit_coin` | 5 | Exact, between tiers, dust, reserve, float("inf") |
| `infer_designation_by_size` | 4 | tier_spare, dust, reserve, unknown |

**29 new tests** in `tests/test_plan_02_16_coin_classifier_unit.py`.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
