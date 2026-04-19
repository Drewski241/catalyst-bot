# Findings — Slice 02-02

Unit test expansion for `api_server.py` — pure helpers and core endpoint shapes.

---

## Existing coverage (before this slice)

`tests/test_api_local_guard.py` (14 tests) covers:
- Token injection in root page
- Auth guard on write endpoints
- Rate-limit exemptions (splash_incoming)
- open-external URL validation
- Config POST update response shape
- Coin prep status endpoint
- Sage version checking
- Smart defaults Dexie v1 params

---

## New coverage added

| Function/Endpoint | Tests | Notes |
|-------------------|-------|-------|
| `_is_loopback_addr` | 8 | IPv4 loopback/8 range, IPv6 ::1, localhost, invalid inputs |
| `_safe_float` | 6 | None, float, Decimal, str, invalid, int |
| `_serialize_dict` | 5 | Decimal→str, nested, None, list-of-dicts |
| `_is_rate_limited` | 4 | First call, below max, over max, endpoint isolation |
| `GET /api/bot/state` | 2 | bot=None→500, bot with state→200 |
| `GET /api/config` | 3 | Public read (no token required), flat dict shape |
| `POST /api/bot/start` | 2 | Requires token, already_running response |
| `POST /api/bot/stop` | 2 | Requires token, bot=None→500 |

**32 new tests** in `tests/test_plan_02_02_api_server_unit.py`.

---

## Observations (non-bugs)

- `GET /api/config` is a **public read endpoint** — no token required. This is intentional
  (the GUI reads config before the user logs in). Sensitive values are excluded via
  `cfg._SENSITIVE_KEYS`. Not a security issue.
- `_serialize_list` only converts dicts inside lists — bare Decimals in a list are
  passed through as-is. Consistent with how fill/offer lists are structured (always
  list-of-dicts), not a bug.
- `POST /api/bot/stop` returns 500 when `bot=None`. This is consistent with `start` —
  both require the bot object to be initialised (which happens on first API call).

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
