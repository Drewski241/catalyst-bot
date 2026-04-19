# Findings — Slice 03-18

Integration tests for orphan coin cleanup: cleanup_orphaned_locked_coins + check_orphan_locks.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestCleanupOrphanedLockedCoins` | 9 | no-op, null trade_id, stale trade_id, active kept, wallet-confirmed skip, mixed, stats, free pool, CAT coins |
| `TestCheckOrphanLocks` | 5 | pass when clean, pass with open offer, detect null trade_id, detect stale trade_id, auto_repair frees |
| `TestOrphanCleanupCycle` | 2 | full cancel flow, partial cancel with 3 offers |

**16 new tests** in `tests/test_plan_03_18_orphan_coin_cleanup_integration.py`.

## Isolation fix required

`test_coin_manager_exact_selectable.py` tearDown pops `"database"` from `sys.modules`.
`check_orphan_locks` uses lazy `from database import get_connection` — after the pop,
Python re-imports a fresh module with the default DB_PATH instead of the temp path,
causing the SQL query to return no rows and the check to return "pass" incorrectly.

**Fix:** `_TempDB.setUp` and `tearDown` now re-register `sys.modules["database"] = _db`
to pin the cached module object. Same pattern as the 02-24 config isolation fix.

## No bugs found in production code
