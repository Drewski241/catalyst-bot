# Slice 06-01: taker fill against bot's top buy offer

**Layer:** 6 (live-fire) · **Estimated time:** ~45 min elapsed
(~15 active, rest waiting for confirms + observation window) ·
**Requires:** human operator + secondary wallet with CAT to sell.

## Goal

Verify that when an external taker accepts the bot's top buy offer
(bot buys CAT for XCH), every tab reflects the fill accurately within
its expected timing window, and the ladder refills cleanly on the next
cycle.

## Preconditions

### Wallet state
- **Primary wallet** (bot): Test Wallet 6 (fingerprint `2981073251`)
  - XCH: ≥ 20 XCH spendable
  - CAT (Monkeyzoo): any amount (fill will increase it)
  - Liquidity mode: `two_sided` (so round-trip PnL can match later)
  - Bot: **running** for ≥ 1 full cycle (ladder established)
- **Secondary wallet** (taker): a separate Sage fingerprint OR a Chia
  reference wallet, with:
  - ≥ 1 XCH (for change + fee)
  - ≥ (the inner-tier CAT amount) of MZ — you need to be able to SELL
    enough CAT to accept a top-of-ladder buy offer. Inspect the bot's
    top buy from `/api/offers` for the exact `size_cat`.

### Market state
- Snapshot TibetSwap mid price via `/api/bot/price`
- Confirm no active sniper probes (stale ones can confuse cross-tab
  accounting): `/api/pnl.sniper.active_snipes == 0`

### Bot state before trigger
Open each tab in turn, capture baseline:
- [ ] **Dashboard** — screenshot + note `stats.total_fills`, last-fill-ago
- [ ] **Offers (Active)** — screenshot, note count + top row's trade_id + price
- [ ] **Offers (History)** — screenshot
- [ ] **PnL** — note `pnlTotalFills`, `pnlBuyVolumeXch`, `pnlBuyVolumeCat`, `pnlNetPosition`
- [ ] **Logs** — note timestamp of most recent entry

Also `curl -s http://127.0.0.1:5000/api/pnl > /tmp/pnl_before.json` and
`curl -s http://127.0.0.1:5000/api/offers > /tmp/offers_before.json`.

## Trigger

**Human operator**:

1. Find the bot's top buy offer on Dexie. Either:
   - Open `https://dexie.space/offers/<full_id>` using the Dexie link
     shown in the Offers tab, OR
   - Copy the offer_bech32 from `/api/offers` field
2. In the secondary wallet's Sage, go to **Take Offer** and paste the
   offer. It should resolve to "you receive N XCH, you pay M MZ".
3. Click **Accept** (or equivalent). Confirm in Sage.
4. **Record the trigger timestamp** (`T0`). Everything else is measured
   relative to this.
5. Wait for the swap to confirm on-chain. At the current Chia block
   time that's ~52 seconds per block; a typical offer confirms in 1-2
   blocks.

## Observations (cross-tab matrix)

Tick each when observed. Note the elapsed seconds (from T0) in the
rightmost column; any row missing its signal after the "Expected by"
window is a finding.

| # | Expected outcome | Tab / endpoint | Field / event | Expected by | Observed |
|---|---|---|---|---|---|
| 1 | Mempool watcher detects the spend | Logs | `pool_spend_detected` or `mempool_imminent_fill` | 10 s | ☐ |
| 2 | Fill tracker verifies | Logs | `fill_verified` for the trade_id | 90 s (after confirm) | ☐ |
| 3 | Offer disappears from Active | Offers — Active | row count −1, top trade_id gone | 60 s | ☐ |
| 4 | Offer appears in History | Offers — History | row with same trade_id + `FILLED` | 90 s | ☐ |
| 5 | Total Fills counter increments | PnL | `#pnlTotalFills` +1 | 60 s | ☐ |
| 6 | Buy Volume increments | PnL | `#pnlBuyVolumeXch` + `#pnlBuyVolumeCat` | 60 s | ☐ |
| 7 | Net flow updates (XCH decreases) | PnL | `#pnlNetXchFlow` goes more negative | 60 s | ☐ |
| 8 | Net position (CAT) increases | PnL | `#invNetPosition` positive drift | 60 s | ☐ |
| 9 | Position gauge bar shifts right | PnL | `#invPositionFill` width changes | 60 s | ☐ |
| 10 | Last-fill-ago ticker resets | Dashboard | "X seconds ago" widget | 30 s | ☐ |
| 11 | Bot balances refresh | Dashboard / `/api/status.balances` | CAT up, XCH down | 120 s | ☐ |
| 12 | Coin locked-count adjusts | Dashboard | `xch_locked_coins` decrements by 1 | 90 s | ☐ |
| 13 | Ladder refills on next cycle | Offers — Active | count returns to target | next cycle start + ~10 s | ☐ |
| 14 | No error logs during the observation | Logs | zero `[ERROR]` or warning spikes | throughout | ☐ |
| 15 | SSE stream delivered fill event | DevTools Network → `/api/events` | `fill` message with trade_id | 60 s | ☐ |

### Cross-tab consistency gate

At T0 + 120 s, hit every tab in order (don't refresh). Verify:

- [ ] **16** Dashboard fills count == PnL `#pnlTotalFills`
- [ ] **17** Offer is in exactly ONE of Active / History, not both
- [ ] **18** `/api/pnl` `total_fills` matches all tabs
- [ ] **19** `/api/offers` live offers count matches Dashboard ladder card
- [ ] **20** `/api/status.coin_tracking.xch_locked` matches Dashboard's XCH locked coin count

## Additional sanity

- [ ] Compare `/tmp/pnl_before.json` vs `curl /api/pnl` now:
  - `total_fills`: +1
  - `buy_fills`: +1
  - `unmatched_buy_fills`: +1 (until a sell fill closes the round-trip)
  - `buy_volume_xch`: +(offer's XCH size)
  - `buy_volume_cat`: +(offer's CAT size)
- [ ] If there was a prior unmatched sell fill at a LOWER price, a
  `round_trips` increment + positive `realised_pnl_xch` change should
  also be visible. Note it as a bonus observation.

## Cleanup

The bot will naturally:
- Refill the top-of-ladder buy slot on the next cycle
- Leave the CAT from the fill in the wallet (future sell fills will
  gradually recycle it)

No manual cleanup required unless:
- The test left the position dangerously close to `MAX_POSITION_XCH` —
  flag in spawn_queue for the risk-manager slice
- The secondary wallet needs its CAT restored (out of scope; operator
  handles)

## Success criteria

- All 20 rows in the matrix have `✓` within their expected window
- Zero inconsistencies in the cross-tab gate (rows 16-20)
- Zero ERROR entries in Logs during the observation window
- Ladder back to target count within one cycle
- If any `✗`, file in findings.md with classification:
  - Tier A — backend wrong (DB row missing, API returns stale data)
  - Tier B — backend correct, SSE/frontend lag (tab didn't refresh)
  - Tier C — cosmetic (tab refreshed eventually but after window)

Tier A / B fixes land this slice. Tier C logs to spawn_queue for a
UI-polish session unless the delay is egregious (>5× expected window).

## Escalate to Opus if

- Fill is detected twice (duplicate `fill_verified` events) — this has
  regression history and root cause is rarely in the obvious module
- Realised PnL calculation produces an unexpected sign — round-trip
  matching involves 3 modules and needs careful reasoning
- Cross-tab inconsistency points at an SSE broadcast bug — debugging
  event propagation across threads is usually a deep dive

## Variants to run after this (subsequent slices or rounds)

- 06-02: taker fills bot's top SELL offer (mirror direction)
- 06-03: taker fills 2-3 offers in one swap (multi-fill burst)
- 06-09: taker fills enough to exhaust one tier → topup trigger
- 06-10: fill flips net position (long → short) → inventory skew recalc
