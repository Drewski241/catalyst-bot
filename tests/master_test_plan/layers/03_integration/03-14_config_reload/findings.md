# Findings — Slice 03-14

Integration tests for `Config.reload()` and `Config.update()` with real temp `.env` file I/O.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestConfigReload` | 7 | Initial bool True/False, flip, flip-back, string field, idempotent, multi-cycle |
| `TestConfigUpdate` | 3 | Newline/CR/null-byte injection guards all block and leave field unchanged |
| `TestConfigReloadThreadSafety` | 2 | 10 concurrent reloads no raise; valid bool after 5 concurrent |
| `TestConfigReloadQuoteStripping` | 4 | Single-quoted, double-quoted, unquoted, quoted bool |

**16 new tests** in `tests/test_plan_03_14_config_reload_integration.py`.

## No bugs found

All 16 tests passed on first run.

## Key design note

`_TempEnv` base class clears `DRY_RUN` and `CAT_TICKER_ID` from `os.environ` in setUp
because these env vars are already loaded from the real `.env` at module import time.
Fields with legacy fallback keys (e.g. `MAX_ACTIVE_BUY_OFFERS` → `MAX_ACTIVE_BUY`) cannot
be isolated this way — only fields with a single env key are safe to test via temp `.env`.
