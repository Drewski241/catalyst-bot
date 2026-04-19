# Findings — Slice 02-15

Unit tests for `coin_prep_utils.py` and `coin_prep_worker.py` pure helpers.

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `should_retry_unconsumed_split` | 10 | retries exhausted, elapsed, outputs selectable, pool not intact, custom params |
| `should_extend_pending_consumed_split_grace` | 14 | extensions used, deadline, expected_count, tx state, pool intact, ratio threshold, custom params |
| `PrepPhase` enum | 3 | all 8 members, string values, count |
| `CoinPrepStatus.to_dict` | 5 | percentage key, all fields present, truncation, error field |
| `_prepared_coin_count_from_total` | 5 | normal, 1→0, 0→0, None→0, large |
| `_sage_submit_succeeded` | 8 | None, empty dict, error key, success=False, status error/failed, status ok, non-dict |
| `_extract_sage_transaction_ids` | 8 | None, list, single, nested, dedup, 0x prefix, already 0x, empty ids |
| `_ensure_0x` | 4 | adds prefix, preserves, empty passthrough, None passthrough |
| `CoinPrepWorker._compute_coin_id` | 6 | 0x-prefixed 66-char hex, deterministic, amounts differ, amount=0, amount=128, strips 0x from inputs |

**56 new tests** in `tests/test_plan_02_15_coin_prep_utils_worker_unit.py`.

## Bugs found and fixed

**`test_false_exactly_at_retry_after` — wrong assumption corrected in test**
The guard is `elapsed_s < retry_after_s` (strict less-than), so `elapsed_s == retry_after_s` passes through. Test renamed to `test_true_exactly_at_retry_after` to pin the correct behaviour.
No production code change needed.
