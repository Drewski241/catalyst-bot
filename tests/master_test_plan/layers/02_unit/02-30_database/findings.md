# Findings — Slice 02-30

Unit test expansion for `database.py` — all public functions.

---

## Existing coverage (before this slice)

None — no tests referenced database.py directly.

---

## New coverage added

| Function group | Tests | Notes |
|----------------|-------|-------|
| `norm_coin_id` | 6 | Pure function: 0x prefix, lowercase, None, whitespace |
| `add_offer` / `get_offer` | 5 | Insert, read-back, duplicate, missing, tier storage |
| `update_offer_status` | 3 | Filled, cancelled, unknown-ID (no-op) |
| `get_open_offers` | 4 | Unfiltered, by side, by asset, excludes cancelled |
| `record_fill` / `get_fills` | 3 | Round-trip, filter by side |
| `get_net_position` | 4 | No fills, buy, sell, balanced |
| `upsert_coin` / `lock_coin` / `free_coin` | 4 | CRUD lifecycle, conflict update |
| `get_coin_summary` | 2 | Empty DB, counts free coins |
| `log_event` / `get_recent_events` | 3 | Storage, severity filter, limit |
| `get_setting` / `set_setting` | 4 | Default, round-trip, update, independent keys |
| `record_price` / `get_recent_prices` | 2 | Storage, per-asset separation |

**40 new tests** in `tests/test_plan_02_30_database_unit.py`.

---

## Key discovery: update_offer_status with unknown ID

`update_offer_status("nonexistent", ...)` returns `True` (no-op success). SQLite UPDATE
matching 0 rows is not an error, and the function does not inspect `rowcount`. This is
intentional idempotent behaviour — callers don't need to pre-check existence.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
