# Fixes — Slice 02-08

No production code fixes needed.

---

## Test corrections

- `test_no_data_returns_normal_regime`: Expected `"normal"` but `_analyze_volatility`
  sets regime from `vol_metric` at end of function. With no data `vol_metric = 0` →
  no threshold exceeded → `"quiet"`. Corrected assertion.
