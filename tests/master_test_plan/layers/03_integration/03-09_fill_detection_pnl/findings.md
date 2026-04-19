# Findings — Slice 03-09

Integration tests for fill detection + PnL round-trip matching using a real SQLite temp DB.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestRecordFill` | 4 | stored+retrievable, idempotent, offer marked filled, multi-side |
| `TestGetUnmatchedFills` | 3 | fresh fills unmatched, matched excluded, asset isolation |
| `TestMatchRoundTrip` | 4 | positive rt_id, PnL on both fills, round_trip_id linked, matched→no longer unmatched |
| `TestPnLRoundTripFlow` | 4 | buy→sell round-trip, net pos after unmatched buys, FIFO order, multiple independent trips |
| `TestNetPosition` | 5 | empty=0, buys positive, sells negative, net-zero after pair, cross-asset isolation |

**20 new tests** in `tests/test_plan_03_09_fill_detection_pnl_integration.py`.

## No bugs found
