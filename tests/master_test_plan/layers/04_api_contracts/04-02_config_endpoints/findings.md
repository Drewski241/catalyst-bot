# Findings — Slice 04-02

API contract tests for config endpoints (GET/POST /api/config + reload/apply/live).

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestConfigGet` | 6 | 200 no-token, flat dict shape, required keys, credentials excluded |
| `TestConfigPost` | 9 | 401 no-token, 400 bad body, 403 blocked keys (cert/URL/wallet_type/CAT_ASSET_ID), success/failure |
| `TestConfigReload` | 3 | 401 no-token, reloaded status, cfg.reload() called |
| `TestConfigApply` | 3 | 500 no-bot, reload-on-stopped, 401 no-token |
| `TestConfigLive` | 6 | 401 no-token, 400 bad body/missing fields, 403 blocked key, success path |

**27 new tests** in `tests/test_plan_04_02_config_endpoints.py`.

## No bugs found

All 27 passed on first run.
