# Findings — Slice 04-01

API contract tests for the three core status endpoints.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestBotStateContract` | 9 | bot=None→500, stopped/running→200, required keys, field values |
| `TestBotPriceContract` | 8 | bot=None→500, bot set→200, all three price keys, string types |
| `TestStatusEndpointSmoke` | 8 | bot=None→200, required top-level keys: running/stats/balances/offers/current_cat |
| `TestStatusEndpointWriteGuards` | 4 | POST no-token→401, POST with-token→405 (before_request fires before method guard) |

**29 new tests** in `tests/test_plan_04_01_status_endpoints.py`.

## No bugs found

All 29 tests passed (after one fix: POST returns 401 not 405 because
`enforce_local_runtime_guard` before_request fires before Flask route matching).

## Key findings

1. `/api/status` with `bot=None` makes TibetSwap/Dexie network calls only when
   `_active_cat["asset_id"]` is truthy. Tests clear `_active_cat` to avoid
   network I/O.
2. `_get_health_snapshot()` returns early `{"status": "not_started"}` when
   `sage_node._startup_authorised = False` (default) — no wallet call.
3. `before_request` auth guard intercepts POST without token and returns 401
   before Flask's 405 (method not allowed) fires. This means there is no
   method-enforcement at all for unauthenticated POSTs.
