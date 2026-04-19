# Fixes — Slice 02-16

No production code fixes needed.

---

## Test corrections

- `test_exact_mid_size_matches_mid` was a stale placeholder with an intentionally
  wrong assertion left from mid-edit thinking. Removed it; the correct assertion
  (2T coin → mid tier) is covered by `test_exact_mid_size`.
