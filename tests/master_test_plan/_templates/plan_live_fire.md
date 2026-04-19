# Slice <SLICE-ID>: <TITLE>

**Layer:** 6 (live-fire) · **Estimated time:** <30-90 min elapsed, much
of it waiting> · **Requires:** human operator + secondary wallet.

## Goal

One sentence. The observable outcome you're confirming the bot handles
correctly end-to-end.

## Preconditions

### Wallet state
- **Primary wallet** (bot): Test Wallet 6 (fingerprint `2981073251`)
  - XCH: <amount or range>
  - CAT: <amount or range>
  - Liquidity mode: <two_sided / buy_only / sell_only>
  - Bot: <running / stopped>
- **Secondary wallet** (taker): <which one, e.g. Test Wallet 7>
  - Must have enough XCH + CAT to execute the trigger action
  - Must be on the same Sage instance OR a separate wallet (specify)

### Market state
- Current TibetSwap mid ≈ <price snapshot>
- Pool depth: <X XCH liquid>
- Dexie orderbook: <briefly — typical competitor spread>

### Bot state before trigger
Capture baseline — take a screenshot of each tab BEFORE triggering so
the "after" can be compared exactly.

Tabs to capture:
- [ ] Dashboard (stats card, ladder summary)
- [ ] Offers — active table count + topmost 3 rows
- [ ] PnL — hero cards (Session, Round Trips, Total Fills)
- [ ] Logs — last event timestamp
- [ ] (optional) Intel — active pool depth

## Trigger

**The human operator performs:**

1. <Concrete step 1 — e.g. "Open Sage with secondary wallet">
2. <Step 2 — e.g. "Paste the bot's top buy offer from Dexie into the secondary Sage">
3. <Step 3 — e.g. "Confirm the atomic swap">
4. <Step 4 — e.g. "Wait ≤3 blocks for on-chain confirmation">

Record the trigger timestamp (local time) — everything after is
measured from this point.

## Observations (cross-tab matrix)

For each expected outcome, note which tab it should appear in + the
timing window. Delay >= "Expected by" is a finding.

| Expected outcome | Tab | Element / field | Expected by (secs after trigger) | Result |
|---|---|---|---|---|
| Fill event logged | Logs | `fill_verified` event | 30 | ☐ |
| Offer moves active→history | Offers | top row disappears from Active | 15 | ☐ |
| Offer appears in history | Offers | top of History tab | 30 | ☐ |
| Total Fills counter increments | PnL | `#pnlTotalFills` | 15 | ☐ |
| Realised PnL updates (if round-trip) | PnL | `#pnlRealised` + `#pnlAvgTripPnl` | 60 | ☐ |
| Volume Breakdown increments | PnL | Bought / Sold / Net Flow row | 30 | ☐ |
| Inventory position gauge moves | PnL | `#invNetPosition` + `#invPositionFill` width | 30 | ☐ |
| Dashboard counter | Dashboard | fills count, last-fill-ago ticker | 15 | ☐ |
| Ladder refill on next cycle | Offers | active count returns to target | next cycle (~45 s) | ☐ |
| Coin inventory decrements | Dashboard | `xch_trading` / `cat_trading` count | 30 | ☐ |

**Cross-tab consistency check**: after 60s post-trigger, open every tab
in sequence (WITHOUT refreshing the browser) and verify the same fill
is represented consistently. A value like "Total Fills" must match
between Dashboard and PnL — mismatch is a finding.

## Additional checks (optional)

- [ ] SSE stream in DevTools shows a `fill_verified` event
- [ ] Log export contains the fill row
- [ ] `/api/pnl` reflects the update on direct query
- [ ] Database `fills` table has the expected row

## Cleanup

What, if anything, needs restoring after this test so the next session
starts clean. E.g.:
- Restore the secondary wallet's state (return the CAT)
- Re-run coin prep if the ladder shape was distorted
- Reset risk-manager baseline if the fill tripped it near the limit

## Success criteria

- Every row in the observation matrix has `✓` within the expected time
- Zero mismatches between tabs
- Logs show no errors / warnings attributable to the fill
- Bot naturally restores full ladder on next cycle

## Failure handling

For any `✗`:
- Record in findings.md with: tab, field, expected, actual, delay
- Attach timestamped screenshots (before + after)
- Classify as: (a) UI lag (backend correct), (b) backend correct but
  SSE didn't fire, (c) backend wrong
- Escalate to Opus only if (c) and root cause spans multiple modules.
