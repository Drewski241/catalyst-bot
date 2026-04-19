# Findings — Slice 02-21

Unit tests for `wallet_sage.py` pure functions (no RPC calls).

---

## New coverage added

| Function | Tests | Notes |
|----------|-------|-------|
| `_rpc_succeeded` | 9 | None/non-dict, success=False, error/error_message/status keys |
| `_is_cat_wallet` | 3 | XCH wallet_id → False, CAT → True |
| `_extract_sage_coin_list` | 8 | coins/records/data keys, fallback to first list value, filter non-dicts |
| `_normalize_sage_coin_records` | 7 | min/max filters, alternate field names (amt, parentCoin, name) |
| `is_offer_time_expired` | 6 | valid_times.max_time and top-level max_time, past/future |
| `get_offer_expiry_info` | 4 | no max_time → inf, past/future, max_time in result |
| `cat_to_mojos` | 4 | standard, truncation, 0 decimals, sub-unit floor |
| `xch_to_mojos` | 4 | 1 XCH, sub-mojo truncation, zero, floor not round |
| `_is_open_status` | 10 | int 0-3, string open/closed sets, unknown→False, expired record |
| `classify_offers_from_list` | 8 | empty, non-dicts, buy/sell/closed, mixed, wrong asset/pair |
| `_normalize_offer_lock_id` | 6 | non-string→None, empty→None, 0x strip, lowercase, whitespace |

**69 new tests** in `tests/test_plan_02_21_wallet_sage_unit.py`.

---

## No bugs found
