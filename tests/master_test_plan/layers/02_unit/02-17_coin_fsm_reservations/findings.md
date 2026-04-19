# Findings — Slice 02-17

Unit tests for `coin_fsm.py` and `coin_reservations.py`.

---

## Existing coverage (before this slice)

None.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `STATUSES` / `DESIGNATIONS` vocabulary | 5 | membership, type checks |
| `CoinState` dataclass | 3 | str repr, frozen, equality |
| `is_terminal` | 4 | spent, free, locked, gone |
| `validate_transition` | 13 | identity, legal edges, terminal, unknown values, reason strings |
| `_normalise` | 5 | empty, 0x strip, lowercase, clean, whitespace |
| `ReservationRegistry.reserve` | 5 | returns ids, is_reserved, contested skip, same-owner refresh, empty inputs |
| `ReservationRegistry.release` | 3 | frees, wrong owner skips, returns count |
| `ReservationRegistry.release_by_owner` | 2 | frees all, returns count |
| `ReservationRegistry.is_reserved_by` | 1 | owner check |
| `ReservationRegistry.filter_unreserved` | 1 | excludes reserved |
| `ReservationRegistry.gc_expired` | 1 | removes stale (via _gc_locked with future now) |
| `ReservationRegistry.is_reserved` expired | 1 | lazy cleanup via now= injection |
| `ReservationRegistry.stats` | 2 | keys present, contested counter |

**49 new tests** in `tests/test_plan_02_17_coin_fsm_reservations_unit.py`.

---

## Test corrections

- `test_gc_expired_removes_stale` and `test_expired_reservation_not_seen`:
  `reserve()` enforces `ttl_seconds = max(1.0, ...)` so sub-second TTL never
  expires during a 10ms sleep. Fixed by:
  - `gc_expired`: calling `_gc_locked(time.time() + 10.0)` directly under lock
  - `is_reserved`: passing `now=time.time() + 10.0` (exposed parameter)

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
