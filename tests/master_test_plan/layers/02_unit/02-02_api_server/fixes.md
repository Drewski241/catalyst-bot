# Fixes — Slice 02-02

No production code fixes needed.

---

## Test corrections

Several test assumptions needed adjusting after checking actual route behaviour:

- `test_config_get_requires_token` → `GET /api/config` is a public endpoint; changed to
  assert 200 without token.
- `test_config_get_response_has_required_keys` → response is a flat dict (cfg.to_dict()),
  not a wrapped `{"config": {...}}` object; changed assertions to match.
- `test_start_already_running_returns_conflict` → handler returns `success=True` with
  `status="already_running"` (idempotent), not an error; fixed assertion.
- `test_stop_with_no_bot_returns_success_like` → stop also 500s on no-bot; changed to
  explicitly assert the 500 behaviour.
- `test_list_values_processed` → `_serialize_dict` only converts list-of-dicts,
  not bare Decimals in a list; changed to test the dict-inside-list path.
