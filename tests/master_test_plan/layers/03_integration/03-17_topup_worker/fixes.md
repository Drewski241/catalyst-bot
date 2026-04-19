# Fixes — Slice 03-17

## Bug found during test writing

**`_TempDB.setUp` called `_db.init_db()`** — function does not exist. The correct
name is `_db.init_database()`. Fixed immediately (no production bug; test-only
naming error from copy-paste of an older base-class pattern).

No production bugs found.
