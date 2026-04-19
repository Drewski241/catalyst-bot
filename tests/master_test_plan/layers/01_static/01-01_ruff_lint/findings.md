# Findings — Slice 01-01

Baseline: 543 violations. After auto-fix: 95. After manual fixes: 58 (0 F821, 0 F811).

---

## Finding F1: wallet_sage.get_wallet_puzzle_hashes uses log_event without importing it

**Check:** 3.1 · **Severity:** high · **Status:** fixed

### Reproduction
```
# Any call that reaches the log_event branches (RPC error, bech32m missing,
# loaded, or empty) → NameError: name 'log_event' is not defined
import wallet_sage; wallet_sage.get_wallet_puzzle_hashes(force=True)
```

### Root cause
`get_wallet_puzzle_hashes` (wallet_sage.py:3652) calls `log_event` 4 times but
never imports it. Only local import in the file is inside a different function.

### Resolution
- [x] Fix committed: c3d5cb3
- [x] Regression test: `tests/test_plan_01_01_ruff_fixes.py::TestWalletSageLogEventImport`
- [x] No regressions in `pytest -q`

---

## Finding F2: api_server.api_token_overview calls _req.get() without importing requests

**Check:** 3.1 · **Severity:** high · **Status:** fixed

### Reproduction
```
GET /api/token_overview?dexie_asset_id=<64-char-hex>
→ NameError: name '_req' is not defined
```

### Root cause
`api_token_overview` (api_server.py:9752) uses `_req.get(...)` but has no
`import requests as _req`. Every other caller in the file imports it locally
inside the function body — this one was forgotten.

### Resolution
- [x] Fix committed: c3d5cb3
- [x] Regression test: `tests/test_plan_01_01_ruff_fixes.py::TestApiTokenOverviewRequestsImport`
- [x] No regressions in `pytest -q`

---

## Finding F3: coin_manager._two_step_split references cat_token_amount (not a parameter)

**Check:** 3.1 · **Severity:** high · **Status:** fixed

### Reproduction
```
# Chia wallet + CAT topup path reaches line 5700:
# cli_coin_size = Decimal(str(cat_token_amount or ...))
# → NameError: name 'cat_token_amount' is not defined
```

### Root cause
`_two_step_split` (coin_manager.py:5340, ends 5847) doesn't have
`cat_token_amount` as a parameter. The name belongs to `_smart_topup_wallet`
which is a different method ending at line 4931.

### Resolution
- [x] Fix committed: c3d5cb3
- [x] Regression test: `tests/test_plan_01_01_ruff_fixes.py::TestTwoStepSplitCatTokenAmount`
- [x] No regressions in `pytest -q`

---

## Finding F4: database.py dead record_config_change (3-arg) overrides F26 version (5-arg)

**Check:** 3.1 · **Severity:** medium · **Status:** fixed

### Reproduction
```python
from database import record_config_change
# In Python the last def wins — old 3-arg at line 3526 was overridden
# but was dead code and used a narrower INSERT missing source/note columns
```

### Root cause
F26 (2026-04-08) added `record_config_change(key, old_value, new_value, source, note)`
at line 3792 but did not remove the original 3-arg version at line 3526.

### Resolution
- [x] Fix committed: c3d5cb3
- [x] Regression test: `tests/test_plan_01_01_ruff_fixes.py::TestDatabaseRecordConfigChange`
- [x] No regressions in `pytest -q`

---

## Finding F5: wallet_chia dead count_suitable_coins; caller passes tolerance as is_cat

**Check:** 3.1 · **Severity:** high · **Status:** fixed

### Reproduction
```python
# wait_for_coin_confirmations calls:
#   count_suitable_coins(wallet_id, size, tolerance)  ← positional
# New signature: (id, size, is_cat=False, decimals=3, tolerance=0.1)
# So tolerance=0.25 → is_cat=True for ALL Chia wallet coin waits
```

### Root cause
Old 3-arg `count_suitable_coins` at wallet_chia.py:386 was silently overridden
by new 5-arg version at line 1195. The caller at line 725 used positional args
and accidentally bound `tolerance` to the `is_cat` parameter.

### Resolution
- [x] Fix committed: c3d5cb3
- [x] Regression test: `tests/test_plan_01_01_ruff_fixes.py::TestWalletChiaCountSuitableCoins`
- [x] No regressions in `pytest -q`

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open |
| 5 | fixed |
| 0 | blocked |
