# Fixes — Slice 02-30

No production code fixes needed.

---

## Test corrections

- `test_returns_false_on_unknown_trade_id` initially asserted `False` for an unknown
  trade ID. Actual behaviour is `True` (no-op success — SQLite UPDATE of 0 rows does not
  raise; function returns True without checking rowcount). Renamed test and flipped assertion.
