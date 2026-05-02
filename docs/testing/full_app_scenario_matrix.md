# CATalyst Full-App Scenario Matrix

Purpose: give CATalyst a single source of truth for thorough testing. Each
scenario describes a real condition the bot can face, the expected bot reaction,
the logs and dashboard evidence a user should see, the guidance advice that
should or should not fire, and the safest test layer for proving it.

This document is intentionally scenario-first. The code tests should be small
and atomic underneath it, but the user experience must be verified as a full
chain: trigger -> backend decision -> wallet/Dexie/Sage state -> dashboard
state -> frontend log wording -> guidance.

## Test Layers

| Layer | Purpose | Safe for funds? | Evidence |
|---|---|---:|---|
| Atomic unit | One decision in one module | yes | pytest assertion |
| Integration simulation | Multiple modules with fake wallet/Dexie/Tibet/Spacescan | yes | pytest assertion plus event list |
| UI contract | Browser/API checks for dashboard, logs, alerts, copy | yes | Playwright screenshot/console/API dump |
| Replay | Parse a real superlog/API snapshot and verify expected timeline | yes | replay report |
| Live runbook | Real Sage wallet, real offers, real TibetSwap, real chain latency | no | timestamps, screenshots, DB/API/log snapshots |

Rule: live tests should only be used after the equivalent atomic or integration
expectation exists. Live testing then validates external timing and service
behavior, not basic logic.

## Evidence Contract

Every scenario should eventually define:

| Field | Meaning |
|---|---|
| Trigger | What starts the scenario |
| Expected backend path | Main modules/functions expected to react |
| Expected action | What the bot should do |
| Backend log events | `log_event` / `slog` event names expected |
| Frontend log | What the user should see in app logs |
| Dashboard | Cards/counts/charts that should change |
| Guidance | Alert or recommendation expected |
| Must not happen | Regressions or scary/noisy messages that must stay absent |
| Settle condition | The observable state that means the scenario completed |
| Coverage target | Atomic, integration, UI, replay, live |

## Status Legend

| Status | Meaning |
|---|---|
| covered | Existing automated coverage appears sufficient |
| partial | Some code paths covered, but user-facing chain is not |
| gap | Needs new test coverage |
| live-only | Cannot be fully simulated yet; needs live runbook evidence |
| unknown | Needs code audit before assigning status |

## Scenario Matrix

### A. Setup, Onboarding, and Config

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| SETUP-01 | Fresh app launch with no config | Show startup gates in order; no trading starts | Dashboard blocked, clear setup actions | No trading warnings before config exists | UI + integration | partial |
| SETUP-02 | Sage closed at launch | App waits for Sage; does not kill or close Sage on app exit | Wallet panel says Sage unavailable/retry | Suggest open Sage, not coin prep | UI + integration | partial |
| SETUP-03 | Sage RPC reachable but not synced | Start blocked until synced | Wallet status unsynced | Explain wallet sync wait | UI + integration | partial |
| SETUP-04 | Wrong Sage fingerprint selected externally | Detect mismatch and persistent warning | Banner/guidance identifies fingerprint mismatch | Recommend switching wallet back or reconnecting | integration + UI | partial |
| SETUP-05 | CAT selected with decimals/ticker/name | Persist CAT identity and use correct display units | Token chip and balances correct | No duplicate setup prompt | unit + UI | partial |
| SETUP-06 | Spacescan free tier | Market health uses free-tier wording | Holders/risk show free-tier copy | No error warning for free tier | UI | partial |
| SETUP-07 | Spacescan Pro key invalid | Disable Pro-only fields gracefully | Warning/toast, no crash | Suggest checking API key | integration + UI | gap |
| SETUP-08 | Splash skipped | Splash disabled but bot can trade via Dexie | Splash status disabled | No Splash error guidance | UI | partial |
| SETUP-09 | Splash enabled but daemon missing | Start/install path or clear warning | Splash card not ready | Suggest Splash setup, not wallet repair | integration + UI | partial |
| SETUP-10 | Config save and reload | Values round-trip through `.env` | Reload shows same settings | No stale pending-changes banner | unit + UI | partial |

### B. Settings Modes and Smart Settings

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| MODE-01 | Two-sided balanced Smart Settings | Produce buy and sell ladder, sniper allowed | Buy/sell counts, tier sizes, topup pools | No warning if affordable | unit + API + UI | partial |
| MODE-02 | Buy-only Smart Settings | Disable sell side, disable sniper, CAT topup pool zero | Sell controls hidden/zeroed; active side buy | No sell-side shortage guidance | unit + API + UI | partial |
| MODE-03 | Sell-only Smart Settings | Disable buy side, disable sniper, XCH topup pool zero | Buy controls hidden/zeroed; active side sell | No buy-side shortage guidance | unit + API + UI | partial |
| MODE-04 | Switch mode while bot running | Block change until stopped | Settings locked/toast | Tell user stop bot first | UI + integration | gap |
| MODE-05 | Reverse buy ladder in two-sided mode | Buy tier sizes invert by position, coin buckets remain correct | Buy row visibly reversed | No tier drift false positive | unit + UI | partial |
| MODE-06 | Reverse buy ladder in sell-only | Force disabled/not relevant | Toggle hidden/disabled | No reverse-buy advice | UI | gap |
| MODE-07 | Reserve percentage matrix | Trade sizes and slots scale with reserve | Smart Settings summary changes coherently | Warn only if impossible | API + unit | partial |
| MODE-08 | Low wallet balance Smart Settings | Reduce ladder or fail with clear reason | Impossible banner or smaller ladder | Recommend add funds if needed | unit + API + UI | gap |
| MODE-09 | Existing open offers when settings change | Require stop/rebuild path; no silent shape mismatch | Start blocked if coin sizes stale | Prefer live topup/rebuild before coin prep | integration + UI | partial |
| MODE-10 | One-sided PnL wording | PnL explains accumulation/distribution mode | Single-sided banner; no two-sided market-maker copy | No irrelevant round-trip pressure advice | UI | gap |

### C. Coin Prep and Startup Lifecycle

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| PREP-01 | Fresh two-sided coin prep | Cancel existing offers first, wait for cancel confirmation, split coins | Progress phases; counts update | No scary errors during expected waits | integration + live | partial |
| PREP-02 | Buy-only coin prep | Prepare XCH active-side coins only plus fees | Coin summary single buy column | No CAT shortage warning | integration + live | gap |
| PREP-03 | Sell-only coin prep | Prepare CAT active-side coins only; keep XCH fee pool if needed | Coin summary single sell column | No XCH ladder shortage warning | integration + live | gap |
| PREP-04 | Coin prep with existing fills | Show history-choice modal | Modal includes exact counts/PnL | No hidden reset | UI + integration | partial |
| PREP-05 | User cancels coin prep mid-run | Worker stops safely; app can restart | Prep canceled state; no stuck busy flag | Suggest rerun prep only if coins incomplete | integration + live | partial |
| PREP-06 | Coin prep worker crash | Fail closed with reason | Failed modal has actionable cause | Suggest stop/retry prep, not trade | integration | partial |
| PREP-07 | Coin prep cancel offers race | Wait for cancellation confirmation before combining/spending | Logs show wait; no combine until cancels settled | No duplicate cancel noise | integration + live | gap |
| PREP-08 | Pool coin retry warnings | Treat as controlled retry | App logs info/warning with eventual success | Positive outcome visible | replay + live | partial |
| PREP-09 | App closes during coin prep | Worker/process state cleaned or resumable | Restart sees prep status accurately | Clear next action | integration + live | gap |
| PREP-10 | Prep output tier-size drift | Detect drift, allow live topup when possible | Dashboard says reshaping | Coin Prep only if unresolved | unit + integration + UI | partial |

### D. Bot Start, Offer Creation, and Book Shape

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| START-01 | Start two-sided after prep | Create target buy/sell offers | Cycle complete with expected counts | No warnings | integration + live | partial |
| START-02 | Start buy-only after prep | Create buy offers only | Offers tab active buy only | No sell-side missing guidance | integration + live | gap |
| START-03 | Start sell-only after prep | Create sell offers only | Offers tab active sell only | No buy-side missing guidance | integration + live | gap |
| START-04 | Start with stale DB/open Sage offers | Reconcile before creating; no duplicates | Offers tab/Sage/Dexie counts match | If mismatch, recovery guidance specific | integration + live | partial |
| START-05 | Start while coin prep incomplete | Block start | Start disabled/clear reason | Recommend wait or rerun prep | UI + integration | partial |
| START-06 | Start with tier spares low but active offers possible | Build missing offers first, topup later | Active count reaches target before spare refill | No premature coin prep recommendation | integration | partial |
| START-07 | Start with insufficient active-side funds | Reduce ladder if allowed or block with funding advice | Lower max offers or blocked reason | Add funds/re-run Smart Settings, not generic error | unit + integration + UI | gap |
| START-08 | Dexie post failure | Keep local offer state, retry/backoff | App logs rate-limit or error calmly | If persistent, show Dexie issue guidance | integration | partial |
| START-09 | Splash broadcast failure | Dexie path remains primary | Splash card warning only | Suggest Splash only if enabled/needed | integration + UI | partial |
| START-10 | Offer creation coin selection misfit | Reject wrong tier coin and try correct spare | Debug/info log, no broken offer | Coin pool reshaping if persistent | unit + integration | partial |

### E. Price Movement, Requotes, and Shock Protection

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| PRICE-01 | TibetSwap upward price shock | Protect stale sell side; rebuild after cancels settle | Logs mention detected price move and sell requote | No repeated warning spam | unit + integration + live | partial |
| PRICE-02 | TibetSwap downward price shock | Protect stale buy side; rebuild after cancels settle | Logs mention detected price move and buy requote | No repeated warning spam | unit + integration + live | partial |
| PRICE-03 | Mempool seen before confirmed pool move | Wake fast but wait for measurable price when needed | Info log says early signal/await confirmation | No false cancel if move below trigger | unit + replay + live | partial |
| PRICE-04 | Multi-step whipsaw while cancels pending | Settle pending cancels before more defensive churn | One defer notice per interval; final rebuild | No cancel/recreate fight | integration + live | partial |
| PRICE-05 | Pending cancels block replacement | Defer replacement calmly | App logs defer with positive later outcome | No health pile-on | integration + UI | partial |
| PRICE-06 | Price move below trigger | No defensive cancel; maybe info-level ignore | Quiet log | No guidance | unit | covered |
| PRICE-07 | Dexie/Tibet disagreement | Use configured pricing strategy and arb-gap logic | Market diagnostics show gap | Warn only if stale/unhealthy | unit + integration | partial |
| PRICE-08 | Price oracle stale | Pause creation/requote as configured | Market health stale status | Suggest data-source issue | integration + UI | partial |
| PRICE-09 | Circuit breaker threshold hit | Stop creating/cancel as configured | Circuit breaker badge/log | Clear action to wait/review settings | unit + integration + UI | partial |
| PRICE-10 | Probe/sniper expires | Remove/rearm after configured lifespan | Sniper probe status clears/rearms | No stale probe protection forever | unit + integration + live | partial |

### F. Fills, PnL, and Position

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| FILL-01 | Sell offer taken | Record CAT sold/XCH received, update PnL, rebuild sell if funds | Success fill log, PnL updates | No position drift warning | unit + integration + live | partial |
| FILL-02 | Buy offer taken | Record XCH spent/CAT received, update PnL, rebuild buy if funds | Success fill log, PnL updates | No position drift warning | unit + integration + live | partial |
| FILL-03 | Fill detected after bot-cancelled flag | Verify Dexie/Spacescan and record fill before losing PnL | Log says bot-cancelled but completed | No scary false error | integration + replay | partial |
| FILL-04 | Spacescan unavailable during fill check | Defer verification without double-counting | Info/warning shows retry | No manual reconcile unless persistent | unit + integration | partial |
| FILL-05 | Duplicate fill signal | Single fill row only | PnL unchanged on duplicate | No duplicate guidance | unit | partial |
| FILL-06 | One-sided buy fill | Position accumulates CAT, no round-trip expectation | PnL copy uses accumulate wording | No sell rebuild/guidance | integration + UI + live | gap |
| FILL-07 | One-sided sell fill | Position distributes CAT, no round-trip expectation | PnL copy uses distribute wording | No buy rebuild/guidance | integration + UI + live | gap |
| FILL-08 | External CAT deposit during run | Allocation modal; topup cannot spend until allocated | Guidance allocate deposit | No Run Doctor/position drift | unit + integration + live | partial |
| FILL-09 | External XCH deposit during run | Allocation modal; reserve/topup decision | Guidance allocate deposit | No unexplained PnL drift | unit + integration + live | gap |
| FILL-10 | Actual missing/phantom fill | Raise position sanity with correct action | Guidance manual reconciliation | Doctor only if it can help | unit + integration | partial |

### G. Coin Topup, Reserves, and Reduced Ladders

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| COIN-01 | Active offers missing and spare exists | Rebuild offer before spare topup | Active count recovers quickly | No topup-first delay | integration | partial |
| COIN-02 | Active offers missing and no spare but topup possible | Topup active-side tier first | Topup start/success then offer rebuild | Positive outcome visible | integration + live | partial |
| COIN-03 | Spare buffer low but book complete | Topup can wait/drip | Info-level low spare/topup message | No scary warning unless critical | unit + integration + UI | partial |
| COIN-04 | Topup pool empty | Do not run impossible topup repeatedly | Funds advisory says add/allocate funds | Do not recommend coin prep as first fix | unit + UI | partial |
| COIN-05 | Hard reserve would be breached | Stop creating/cancel or block spend | Reserve floor alert | Recommend add funds/reduce ladder | unit + integration | partial |
| COIN-06 | Wallet RPC balance fails | Defer reserve decision fail-closed | Skipped warning, no false cancel | No reserve breach alert | unit | covered |
| COIN-07 | Unknown deposit-sized coin present | Block topup source until allocation | Allocation prompt | No Doctor | unit + integration + live | partial |
| COIN-08 | Advised deposit allocated to pool | Topup may use coin/budget | Allocation success, topup starts if needed | Clear deposit alert | integration + UI + live | gap |
| COIN-09 | Advised deposit allocated to reserve | Topup must not use hard reserve | Reserve updated | No topup from reserved funds | integration + UI + live | gap |
| COIN-10 | Low funds but smaller ladder possible | Reduce active side target or require Smart Settings rerun | Lower max offers or explicit blocked state | Recommend reduced ladder/add funds | unit + integration + UI | gap |
| COIN-11 | Buy-only low XCH | Buy side shrinks/blocks; ignore CAT shortages | Active buy guidance only | No CAT topup advice | unit + integration | gap |
| COIN-12 | Sell-only low CAT | Sell side shrinks/blocks; ignore XCH shortages | Active sell guidance only | No XCH topup advice | unit + integration | gap |
| COIN-13 | Returned cancel coins arrive late | Fast reconcile before rebuild | Returned coins counted next cycle | No missing-spare warning if settling | integration + live | partial |
| COIN-14 | Misfit absorption after price drift | Absorb only after priority offers/spares handled | Info log, success log | No repeated absorption noise | integration + replay | partial |
| COIN-15 | Fee coin shortage | Replenish fee pool or show fee-specific guidance | Fee pool count low | Do not blame CAT/XCH reserves incorrectly | unit + integration | gap |

### H. Cancel, Restart, and Recovery

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| REC-01 | User stops bot | Stop loop only; do not cancel offers | Bot stopped, offers remain | Explain offers still live | UI + integration | partial |
| REC-02 | User cancel-all while stopped | Cancel all and wait/report progress | Cancel progress and Sage active offers zero | No bot restart until settled | integration + live | partial |
| REC-03 | User cancel-all while running | Block with explanation | Toast/log says stop bot first | No hidden cancel | UI + integration | partial |
| REC-04 | App closes while bot running | Shutdown app, not Sage; bot stops managing offers | App exits, Sage remains open | Warn if offers still live | integration + live | partial |
| REC-05 | Restart with open offers | Reconcile and resume without duplicates | Session recovery or live offer counts | No duplicate creation | integration + live | partial |
| REC-06 | Restart with pending cancels | Wait for settlement before rebuild | Pending cancel count visible | No repeated emergency warning | integration + live | partial |
| REC-07 | Restart after coin prep canceled | Clear or recover busy state correctly | Prep status actionable | Suggest rerun prep if incomplete | integration | gap |
| REC-08 | DB/wallet offer count mismatch | Shape-fix path or guidance with side-specific action | Watchdog alert/action | No generic Doctor unless relevant | integration + UI | partial |
| REC-09 | Orphan locked coins | Free only truly orphaned locks | Info log, coin counts recover | No user action unless persistent | unit + integration | partial |
| REC-10 | WAL/database health issue | Checkpoint or warn with restart action | DB health panel/log | Recommend restart/investigate DB | unit + integration | partial |

### I. External Services and Failure Modes

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| EXT-01 | Dexie 429 | Backoff and retry, no tight loop | Rate-limit info/warning | If persistent, data-source guidance | unit + integration | partial |
| EXT-02 | Dexie 5xx | Retry/backoff; keep local offers | Error after retries | Suggest wait/check Dexie | unit + integration | partial |
| EXT-03 | TibetSwap 429 | Use cached price if safe; mark stale if not | Market data log | No trading if price unsafe | unit + integration | partial |
| EXT-04 | TibetSwap pool unavailable | Fall back or pause based on strategy | Market health degraded | Clear data-source recommendation | unit + integration + UI | partial |
| EXT-05 | Spacescan timeout | Defer enrichment/fill verification | Info/warning not error spam | No false PnL alert immediately | unit + integration | partial |
| EXT-06 | Coinset/mempool unavailable | Disable early shock path but keep normal cycle | Mempool status disabled | No false health failure | unit + integration | gap |
| EXT-07 | Splash daemon no peers | Warn only if Splash enabled | Splash card no peers | Suggest Splash peer/setup | unit + UI | partial |
| EXT-08 | Sage RPC timeout | Fail closed, no destructive action | Wallet status degraded | Suggest Sage/retry, not coin prep | unit + integration + UI | partial |
| EXT-09 | Sage returns empty wallet transiently | Retry/defer before marking coins gone | Coin count retry logs | No reserve breach/cancel cascade | unit + integration | partial |
| EXT-10 | Sage submit returns no txid but chain confirms | Recover via owned/confirmed outputs | Topup/cancel success after retry | No failure modal if recovered | unit + integration | partial |

### J. Dashboard, Logs, and Guidance Contracts

| ID | Scenario | Expected reaction | User-facing evidence | Guidance expectation | Coverage target | Status |
|---|---|---|---|---|---|---|
| UX-01 | Backend logs controlled recovery | App log uses info/success unless user action needed | Calm log feed | No scary repeated warnings | UI + replay | partial |
| UX-02 | Repeated same warning condition | Rate-limit/dedupe | One warning plus later outcome | Guidance remains actionable | unit + UI | partial |
| UX-03 | Positive outcome after deferred action | Log success/info when settled | User sees resolution | Clear stale guidance | UI + replay | partial |
| UX-04 | Percent display | User-facing spread/gap/volatility in percent, not bps | Dashboard and logs use % | Tooltips consistent | unit + UI | partial |
| UX-05 | Market Intelligence chart no data | Show collecting samples or no-data reason | No blank mystery card | No alert unless data source broken | UI | partial |
| UX-06 | Offers depth chart | Axis/labels sensible in two-sided and one-sided modes | No blank/overlap | No guidance | UI | partial |
| UX-07 | Guidance recommends coin prep | Only when stop/rerun settings/prep is truly the solution | Message says stop bot first if needed | No nuclear option for low topup pool | unit + UI | partial |
| UX-08 | Guidance recommends funding | When active side funds/topup pool cannot recover | Specific asset/amount/address | No run Doctor | unit + UI | partial |
| UX-09 | Doctor report all pass | Should not be action for non-diagnostic operational states | Doctor modal only for preflight | No false reassurance loop | UI + integration | partial |
| UX-10 | Text fits cards/buttons | No clipped info boxes or layout overflow | Screenshots desktop/mobile | No hidden action text | UI visual | partial |

## Initial Atomic Test Backlog

These should be implemented before more live stress testing. Each one is small
enough to fail for one reason.

| Priority | Test target | Scenario IDs |
|---:|---|---|
| 1 | Buy-only Smart Settings zeroes sell side, disables sniper, and suppresses sell guidance | MODE-02, START-02, COIN-11 |
| 1 | Sell-only Smart Settings zeroes buy side, disables sniper, and suppresses buy guidance | MODE-03, START-03, COIN-12 |
| 1 | Coin prep launch waits for cancel confirmation before combine/split | PREP-07 |
| 1 | Low topup pool guidance recommends add/allocate funds, not coin prep | COIN-04, UX-08 |
| 1 | Reduced ladder recommendation when active-side funds are low | START-07, COIN-10 |
| 1 | Deposit allocation to pool unlocks topup source; allocation to reserve keeps it protected | COIN-08, COIN-09 |
| 2 | One-sided fill flows do not expect round trips or inactive-side rebuilds | FILL-06, FILL-07 |
| 2 | Price-shock defer warning produces a later positive outcome log | PRICE-04, PRICE-05, UX-03 |
| 2 | Mempool/Tibet shock log appears early enough for advertised early-spotting | PRICE-03, UX-01 |
| 2 | Fee coin shortage produces fee-specific guidance | COIN-15 |
| 2 | App shutdown does not close Sage and warns about live offers | REC-04 |
| 3 | Spacescan/Tibet/Dexie degraded copy is service-specific and not scary | EXT-01 to EXT-05 |
| 3 | Market Intelligence and Offers charts render no-data states correctly | UX-05, UX-06 |

## Live Test Runbook Gates

Before any live test:

1. Commit or stash code so there is a rollback point.
2. Record current branch and commit.
3. Export `/api/status`, `/api/alerts`, `/api/coins`, `/api/dashboard`.
4. Record active Sage offers by RPC.
5. Confirm wallet balances and hard reserves.
6. Decide whether the test may create/cancel/fill real offers.
7. Define the settle condition and stop condition.

During the live test:

1. Capture the trigger time in local time.
2. Tail superlog and app logs.
3. Snapshot `/api/status`, `/api/alerts`, `/api/coins`, `/api/dashboard` after
   each major phase.
4. Record screenshots for dashboard/guidance/logs.

After the live test:

1. Confirm Sage/Dexie/DB offer counts match.
2. Confirm no stale alerts remain.
3. Confirm no repeated warning loops.
4. Record pass/fail and any new atomic test required.

## Known Coverage Gaps Found During Inventory

1. The manual checklist exists, but it is a click checklist, not a scenario
   expectation matrix.
2. `tests/run_tests.py` advertises a `tests/simulation` package for matrix,
   API, stress, and replay testing, but that package is not present in the
   working tree. Either restore/remove/update this runner before relying on it.
3. One-sided trading has unit/API coverage in places, but the full chain
   (Smart Settings -> Coin Prep -> Start Bot -> Fill -> Topup -> PnL -> Guidance)
   needs explicit scenario tests and at least one small live run per side.
4. Replay testing from real superlogs would be valuable and is not currently
   wired as a maintained test layer.
5. Guidance correctness needs its own contract tests: many recent issues were
   correct backend behavior with misleading advice.
