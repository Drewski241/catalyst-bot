# Findings — Slice 02-10

Unit tests for `coinset_client.py` — Coinset blockchain API client.

---

## Existing coverage (before this slice)

None — no tests referenced this module directly.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `_extract_puzzle_hashes` | 6 | None, non-dict, coin_records format, confirmed_records fallback, dedup, missing key |
| `_format_as_wallet_response` | 4 | spent filtered, _source key, success flag, empty list |
| `get_stats` | 5 | all-zero init, mode sage_compat, mode initialized, mode pending_init, puzzle_hashes_cached count |
| `_record_api_call` | 2 | increments total, increments by method |
| `_record_api_error` | 1 | increments counter |
| `get_stats hit_rate` | 1 | zero queries → 0.0% |
| guard clauses | 8 | disabled, empty coin_id, height ≤ 0, empty hint, rate-limited, get_additions empty hash |
| `verify_coin_spent_on_chain` | 4 | not found→None, spent_block_index>0→True, 0→False, 0x prefix normalised |
| `get_spendable_coins` | 4 | not_initialized→fallback, missing wallet→fallback, coinset success, coinset exception→fallback |

**35 new tests** in `tests/test_plan_02_10_coinset_client_unit.py`.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |

---

## Key patching note

`get_stats` does `from config import cfg as _cfg` inside the method body.
Must patch BOTH `coinset_client.cfg` (module attr) AND `config.cfg` (the import source)
to fully control behaviour in tests.
