# Fixes — Slice 03-18

No bugs found in production code. All 16 tests passed once isolation was corrected.

## Test isolation fix

**File:** `tests/test_plan_03_18_orphan_coin_cleanup_integration.py`
**Root cause:** `test_coin_manager_exact_selectable.py` tearDown removes `"database"` from
`sys.modules`; subsequent lazy imports inside `check_orphan_locks` get a fresh module.
**Fix:** `_TempDB.setUp/tearDown` pin `sys.modules["database"] = _db`.
