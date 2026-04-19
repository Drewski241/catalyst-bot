# Findings — Slice 03-12

Integration tests for the cancel-all flow: open offers in DB → OfferManager.cancel_all() → DB status updates.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestCancelAllConfirmed` | 6 | no offers, single, multiple, failed leaves open, mixed, return dict |
| `TestCancelAllPending` | 1 | submitted_pending_confirm leaves offer as "open" in DB |
| `TestCancelAllSideFilter` | 3 | buy-only, sell-only, no filter (all sides) |
| `TestCancelAllExceptionHandling` | 1 | RPC exception doesn't crash caller, offer not marked cancelled |

**11 new tests** in `tests/test_plan_03_12_cancel_all_flow_integration.py`.

## No bugs found

CANCEL_PENDING_METHODS (submitted_pending_confirm, etc.) correctly leave DB
status as "open" — confirmed expected behaviour documented in test.
