# Findings — Slice 02-20

Unit tests for `wallet.py` — backend dispatch layer.

---

## Existing coverage (before this slice)

None. The module is a pure re-export layer with no testable business logic.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `get_wallet_type()` | 4 | returns str, known backend, matches constant, lowercase |
| `WALLET_ID_XCH` constant | 2 | int, positive |
| API surface export check | 1 | 16 required names all present |
| Core callables | 9 | create_offer, cancel_offer, get_spendable_coins, split_coins_rpc, etc. |
| Sage-specific export | 1 | sage_delete_offer only tested when sage backend active |

**17 new tests** in `tests/test_plan_02_20_wallet_unit.py`.

---

## Note

The module contains no business logic beyond the dispatch decision (made at
import time from `WALLET_TYPE` env var) and `get_wallet_type()`. Tests verify
that the API contract (all required public names exported, callables callable)
is upheld for the active backend.

---

## No bugs found
