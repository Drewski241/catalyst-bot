# Fixes — Slice 03-14

No bugs found. All 16 tests passed on first run.

## Design iteration (pre-run)

Initial draft tested `MAX_ACTIVE_BUY_OFFERS` but the real `.env` has `MAX_ACTIVE_BUY=24`
which shadows it via legacy fallback. Rewrote to use `DRY_RUN` / `CAT_TICKER_ID` (no
legacy fallback keys) with explicit env-var clearing in `_TempEnv.setUp`.
