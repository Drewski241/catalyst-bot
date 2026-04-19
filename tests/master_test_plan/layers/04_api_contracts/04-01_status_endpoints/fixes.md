# Fixes — Slice 04-01

No production bugs found.

## Test fix

**Method guard tests expected 405 but got 401.** The `before_request` handler
`enforce_local_runtime_guard` fires before Flask's method-routing check. Any
POST without a valid `X-Bot-Local-Token` header gets 401, not 405. Tests
updated to assert 401 for no-token POSTs, and an additional test verifies
405 when the token IS present.
