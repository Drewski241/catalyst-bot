# Slice 05-22: coin-prep modal — every view + history-choice modal

**Layer:** 5 · **Estimated time:** 50 min · **Escalate to Opus if:** the
history-choice modal's "Keep history" vs "Start fresh" dispatch diverges
from the backend's `full_reset` flag interpretation.

## Goal

Drive the coin-prep modal through all five views (confirm, progress,
complete, error, plus the pre-prep history-choice modal) and verify
each button does what it should.

## Scope

### In-scope
- `#coinPrepConfirmOverlay` + its four internal views
- `#prepHistoryChoiceModal` (shipped 2026-04-19 in commit `095a80d`)
- `startCoinPrepFromModal` flow
- `askPrepHistoryChoice` → keep/fresh/cancel

### Out-of-scope
- Actual on-chain coin splits — use DRY_RUN or mock
- Coin-prep worker internals (slice 02-15)

## Preconditions

- Bot running in `--flask`, Sage connected
- Settings saved with Smart Defaults applied
- (Optional) At least 1 fill in DB so history-choice modal appears

## Checks

### 1. Launch confirm view
- [ ] **1.1** Click "Prepare Coins" button on Dashboard → modal appears
- [ ] **1.2** Shows XCH side + CAT side summary (Coins / Sizes / Total)
- [ ] **1.3** "Yes, Prepare Coins" button shows headroom percent
- [ ] **1.4** Buttons: Back to Settings, Skip Coin Prep, Yes Prepare Coins
- [ ] **1.5** Back button returns to Settings (view-swap, not close)

### 2. History-choice modal (when DB has fills)
- [ ] **2.1** With `/api/pnl/reset-preview` reporting `has_data: true`, clicking "Yes, Prepare Coins" opens `#prepHistoryChoiceModal` FIRST
- [ ] **2.2** Modal body shows exact counts: fills, round trips, PnL XCH, net position
- [ ] **2.3** Three buttons: Keep history (highlighted), Start fresh, Cancel
- [ ] **2.4** Enter key triggers Keep history (default focus)
- [ ] **2.5** "Keep history" sends POST with `full_reset: false`
- [ ] **2.6** "Start fresh" sends POST with `full_reset: true`
- [ ] **2.7** "Cancel" closes modal, no POST sent, confirm button resets text
- [ ] **2.8** With `has_data: false` (fresh install), history-choice modal is SKIPPED

### 3. Progress view
- [ ] **3.1** After POST success, view switches to progress
- [ ] **3.2** Progress bar fills as `/api/coin-prep/status` reports percent
- [ ] **3.3** Phase label animates (Analysing → Cancelling offers → Splitting → Verifying → Done)
- [ ] **3.4** XCH + CAT coin counts populate live
- [ ] **3.5** "Show Coin Prep Logs" expands the rolling log box
- [ ] **3.6** At 100%, the fallback Done button appears (safety net)

### 4. Complete view
- [ ] **4.1** On success, auto-switches to complete view
- [ ] **4.2** Shows summary: total coins prepped, time elapsed
- [ ] **4.3** Done button closes modal, returns focus to Dashboard

### 5. Error view
- [ ] **5.1** Force a failure (e.g. set `XCH_RESERVE` impossibly high → overshoot) → error view shows
- [ ] **5.2** Error message includes the CONCRETE reason (not just "Coin preparation failed!") — verifies the 2026-04-19 `46f7844` fix
- [ ] **5.3** Common causes list visible
- [ ] **5.4** "Try Again" button returns to confirm view
- [ ] **5.5** Close button dismisses modal

### 6. Dismiss / escape
- [ ] **6.1** Clicking outside modal does nothing (destructive action — require explicit click)
- [ ] **6.2** ESC key: closes if on confirm/error/complete view; blocked on progress view
- [ ] **6.3** After close, modal state resets (progress bar at 0, logs cleared)

### 7. Parallel-run guards
- [ ] **7.1** Clicking Yes-Prepare twice rapidly: only one prep job starts (check `/api/coin-prep/status` shows one run_id)
- [ ] **7.2** If a previous prep is still running, UI shows "stale flag" recovery, retries once

## Execution notes

```javascript
// Inspect history-modal state
const modal = document.getElementById('prepHistoryChoiceModal');
const details = document.getElementById('prepHistoryChoiceDetails');
console.log({
  visible: modal.classList.contains('active'),
  detailsHTML: details.innerHTML.slice(0, 500),
});
```

For 2.8 (fresh-install skip), if fills exist you can temporarily wipe
them via `POST /api/pnl/reset` with `{"confirm": "RESET"}` BEFORE the
test — then restore by skipping the restore (next run of the bot
generates new fills anyway).

## Success criteria

- All five views verified
- History-choice modal round-trips cleanly in both keep and fresh paths
- No regressions in `/api/coin-prep/*` endpoints
- Screenshots of each view attached to findings.md
