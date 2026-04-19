# Slice 05-07: Settings — liquidity mode picker end-to-end

**Layer:** 5 · **Estimated time:** 45 min · **Escalate to Opus if:**
mode-hide classes don't propagate cleanly to newly added sections added
by other features.

## Goal

Drive the Liquidity Mode picker from a browser (via Preview MCP) and
verify every documented behaviour.

## Scope

### In-scope
- `#liquidityModeSection` in Settings
- Three radio cards + their highlight / disabled states
- `applyLiquidityModeToBody` body-class wiring
- `mode-hide-on-buy-only` / `mode-hide-on-sell-only` sections actually hiding
- Save round-trip (form → `/api/settings` → `.env`)
- Wallet-aware suggestion (lopsided balance prompt)
- Stop-required gating (can't switch mode while running)

### Out-of-scope
- Backend branching in Smart Settings (slice 04-10)
- Parked-state banner on the Dashboard (slice 05-02)
- PnL banner in single-sided (slice 05-13)

## Preconditions

- Bot running in `--flask` mode on localhost:5000
- Sage connected with Test Wallet 6 (fingerprint 2981073251) OR a
  dev-only mocked wallet profile
- Navigate to Settings view

## Checks

### 1. Render
- [ ] **1.1** Section appears below "Trading Pair", above "Reserves"
- [ ] **1.2** Three cards render: Two-Sided (📈📉), Buy Only (📈), Sell Only (📉)
- [ ] **1.3** Default selected matches `cfg.LIQUIDITY_MODE` from `/api/config`
- [ ] **1.4** Selected card has colour-coded border + background (blue / green / red)
- [ ] **1.5** Non-selected cards are dimmed

### 2. Click-to-switch (while bot stopped)
- [ ] **2.1** Click Buy Only → card highlighted green
- [ ] **2.2** `document.body.className` gains `liquidity-mode-buy-only`
- [ ] **2.3** `getLiquidityMode()` returns `"buy_only"`
- [ ] **2.4** `window._liquidityMode === "buy_only"`
- [ ] **2.5** Click Sell Only → card highlighted red, body class updates
- [ ] **2.6** Click Two-Sided → returns to normal

### 3. Section show/hide under buy_only
- [ ] **3.1** "Max Sell Offers" input hidden
- [ ] **3.2** "Sell ladder sizes" row hidden (all four fields)
- [ ] **3.3** "CAT counts" + "CAT spares" rows hidden
- [ ] **3.4** "Sell (Tokens)" coin-prep summary column hidden
- [ ] **3.5** Inventory Management section hidden
- [ ] **3.6** Reverse Buy Ladder toggle STILL visible (buy-side concept)
- [ ] **3.7** Sniper config hidden; "🎯 Sniper unavailable" banner visible

### 4. Section show/hide under sell_only
- [ ] **4.1** "Max Buy Offers" hidden
- [ ] **4.2** "Buy ladder sizes" hidden
- [ ] **4.3** "XCH counts" + "XCH spares" hidden
- [ ] **4.4** "Buy (XCH)" coin-prep summary column hidden
- [ ] **4.5** Reverse Buy Ladder toggle hidden (N/A for sell)
- [ ] **4.6** Sniper still hidden + banner still shows

### 5. Auto-Fill label adapts
- [ ] **5.1** two_sided: title reads `Auto-Fill Settings`
- [ ] **5.2** buy_only: title reads `Auto-Fill — Accumulation Plan`
- [ ] **5.3** sell_only: title reads `Auto-Fill — Distribution Plan`
- [ ] **5.4** Subtitle text matches mode (check key phrase per mode)

### 6. Save round-trip
- [ ] **6.1** Set mode to buy_only, click "Save & Continue"
- [ ] **6.2** Toast confirms save
- [ ] **6.3** Refresh the page (F5 or via eval `location.reload()`)
- [ ] **6.4** Picker returns to buy_only selection (loaded from env)
- [ ] **6.5** `/api/config` confirms `LIQUIDITY_MODE=buy_only`
- [ ] **6.6** Restore to two_sided before leaving the slice (don't leave test state in env)

### 7. Stop-required gating
- [ ] **7.1** Start the bot (if safe in dev — else skip + document)
- [ ] **7.2** While running, cards have `.disabled` class
- [ ] **7.3** Click a different card → no state change, toast "Stop the bot..."
- [ ] **7.4** `liquidityModeLockedHint` element is visible under the picker
- [ ] **7.5** Stop bot → cards re-enable, hint hides

### 8. Wallet-aware suggestion
- [ ] **8.1** Set CAT reserve very high (simulating 0 usable CAT) → hint should suggest Buy Only
- [ ] **8.2** Clicking "Apply suggestion" button switches mode
- [ ] **8.3** Hint disappears once you're in the suggested mode
- [ ] **8.4** Hint hides while bot is running

## Execution notes

Use the Preview MCP:

```javascript
// Check mode after click
const res = {
  mode: getLiquidityMode(),
  bodyClasses: document.body.className.split(' ').filter(c => c.includes('liquidity-mode')),
  sellHidden: window.getComputedStyle(
    Array.from(document.querySelectorAll('.mode-hide-on-buy-only'))
      .find(el => el.textContent.includes('Sell ladder sizes'))
  ).display === 'none',
};
```

## Success criteria

- Every check has a pass/fail recorded in findings.md
- Any hidden section that SHOULD have been tagged but wasn't → fix the
  tag + regression test
- Mode is restored to two_sided at session end
- A screenshot (paste output from `preview_screenshot`) attached to each
  of the three modes for visual reference
