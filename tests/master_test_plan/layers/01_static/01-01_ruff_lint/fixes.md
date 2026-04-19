# Fixes — Slice 01-01

---

## Fix 73fc1a7: ruff auto-fix pass — 448 findings cleared

**Addresses:** baseline cleanup · **Files touched:** 60+ source files

### Change summary
`ruff check --fix` cleared 337 f-strings without placeholders (F541),
95 unused imports (F401), 8 unused local variable assignments (F841),
3 F811 import redefinitions, and 3 E401 multi-import lines. All mechanical.

### Regression coverage
- Full suite: 506/506 green immediately after applying

### Verified no regressions in
```
pytest -q
```
Result: 506 passed, 0 failed

---

## Fix c3d5cb3: fix 5 real bugs found by ruff F821/F811

**Addresses:** F1, F2, F3, F4, F5 · **Files touched:** `wallet_sage.py`,
`api_server.py`, `coin_manager.py`, `database.py`, `wallet_chia.py`,
`tests/test_plan_01_01_ruff_fixes.py`

### Change summary
Five real bugs (3 NameErrors, 2 dead-function redefinitions) introduced
before the audit. Most critical: `cat_token_amount` in `_two_step_split`
(CAT topup via Chia CLI would always NameError), `log_event` missing in
`get_wallet_puzzle_hashes`, and `_req` missing in `api_token_overview`.

### Regression coverage
- `TestWalletSageLogEventImport::test_get_puzzle_hashes_rpc_error_no_name_error`
- `TestWalletSageLogEventImport::test_get_puzzle_hashes_import_error_no_name_error`
- `TestApiTokenOverviewRequestsImport::test_token_overview_no_name_error_on_request_failure`
- `TestApiTokenOverviewRequestsImport::test_token_overview_empty_id_returns_fast`
- `TestTwoStepSplitCatTokenAmount::test_cat_token_amount_not_referenced_in_source`
- `TestTwoStepSplitCatTokenAmount::test_two_step_split_cat_branch_no_name_error`
- `TestDatabaseRecordConfigChange::test_record_config_change_accepts_source_and_note`
- `TestDatabaseRecordConfigChange::test_only_one_record_config_change_definition`
- `TestWalletChiaCountSuitableCoins::test_count_suitable_coins_tolerance_kwarg`
- `TestWalletChiaCountSuitableCoins::test_wait_for_coin_confirmations_no_type_error`
- Before fix: would FAIL with NameError / TypeError · After fix: PASS

### Verified no regressions in
```
pytest -q
```
Result: 516 passed, 0 failed (+10 new tests)

---

## Lessons / gotchas

- `api_server.py` uses `import requests as _req` inside each function that
  needs HTTP — module-level import is intentionally absent (circular import
  avoidance). Every new HTTP-using endpoint must add its own import.
- `wallet_sage.py` and `wallet_chia.py` both define `count_suitable_coins`
  and `log_event` locally — the `wallet` adapter in `wallet.py` selects the
  right backend. Never import from the concrete wallet module directly.
- Very large functions (>500 lines) in coin_manager.py can hide scope bugs
  that even the developer's IDE won't catch — ruff's `F821` found this one.
