# Fixes — Slice 03-10

No bugs found in production code. Two test fixes during development:

1. **Duplicate trade_id rejection**: `_fake_offer_manager()` initially used `return_value`
   with a fixed trade_id. When both buy and sell used the same id, `add_offer()` skipped
   the second. Fixed by using `side_effect` with a counter.

2. **Side_effect function signature**: `_side_result(**kw)` rejected Mock's positional
   arg (the offer_dict). Fixed to `_side_result(*a, **kw)`.
