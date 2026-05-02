# Full-App QA Run - Live Restart and UI Contract - 2026-05-02

## Scope

This run covered safe testing that did not require an external wallet trade:

- Restart/resume against the existing live Sage book.
- DB/Sage active-offer agreement checks.
- Dashboard, Offers, Market Intelligence, logs, alerts, and Doctor API checks.
- High-risk atomic/integration tests for mode settings, topup, reduced-ladder,
  price/requote, sniper, dashboard percentage display, and guidance wording.
- UI screenshots and basic text-overflow probes.

External-wallet scenarios were deferred intentionally:

- TibetSwap shock/whipsaw trades.
- Taken-offer fill tests.
- Real incoming funds/reserve-choice modal tests.
- Full cancel-all coin-prep runs.

## Baseline

- Catalyst was started in Flask mode with `python desktop_app.py --flask`.
- Sage stayed open as `sage-tauri.exe`.
- Shutdown via the Catalyst API with offer cancellation disabled did not close
  Sage.
- The existing live book resumed without duplicate offer creation.

Observed live state after restart:

| Check | Result |
|---|---|
| Bot running | yes |
| Loop count sampled | 14 |
| DB open offers | 23 buy / 23 sell |
| Frontend log latest cycle | `Cycle #13 complete - 23b/23s active` |
| Pending cancels | 0 |
| Bot errors | 0 |
| Doctor | all 11 checks passed |
| Visible warning/error logs | none in latest API log sample |

## Fixes Made During This Run

### Tier-Size Drift Guidance

The tier-size drift alert previously said live topup had started immediately,
which made the UI feel more certain than the bot state was. The wording now says
the live topup was queued or recently ran, and keeps Coin Prep framed as a later
fallback only if live topup does not resolve the drift.

Evidence:

- `tier_size_drift` alert now reports:
  `Live topup recently ran; retry window opens in 149s. Coin Prep is only needed if this stays unresolved after topup has had time to finish.`
- Unit coverage updated in `tests/test_plan_02_01_bot_loop_unit.py`.

### Sage Cleanup Summary

Startup cleanup could show a scary "anomaly" style summary for historical Sage
records that CATalyst intentionally left alone because the DB did not verify
them as cancelled or expired. The user-facing summary now explains this as a
safe historical-record skip.

Evidence:

- Latest startup message:
  `Skipped 655 historical Sage offer records during safe cleanup (655 first seen this session, 0 already known). They were not DB-verified as cancelled/expired, so CATalyst left them visible in Sage instead of deleting them.`
- Unit coverage added in `tests/test_plan_02_01_bot_loop_unit.py`.

## API and UI Evidence

API endpoints checked:

- `/api/status`
- `/api/alerts`
- `/api/logs`
- `/api/coins`
- `/api/offers`
- `/api/doctor`

Screenshots captured:

- `output/playwright/qa-dashboard.png`
- `output/playwright/qa-offers.png`
- `output/playwright/qa-market-intelligence.png`
- `output/playwright/qa-logs.png`

Observed UI:

- Offers depth chart rendered with 23 active buys and 23 active sells.
- Market Intelligence price chart rendered after refreshing market data.
- Frontend logs were calm: cycle starts/completions, wallet sync, CAT discovery,
  and no repeated warning block in the visible log stream.
- Text-overflow probe found no content overflow in cards/buttons/info boxes.
  The only detected overflow was a collapsed sidebar log badge, which is likely
  a layout false positive because the badge/icon container intentionally clips.

## Automated Test Evidence

Targeted TDD checks:

```text
python -m pytest -q tests\test_plan_02_01_bot_loop_unit.py -q
passed
```

High-risk safe batch:

```text
python -m pytest -q tests\test_full_app_scenario_matrix.py tests\test_liquidity_mode.py tests\test_plan_03_16_liquidity_mode_switch_integration.py tests\test_plan_04_10_smart_defaults_endpoint.py tests\test_plan_04_14_dashboard_endpoint.py tests\test_dashboard_percent_display.py tests\test_dashboard_log_visibility.py tests\test_bot_health_funds_advisory.py tests\test_bot_health_deposit_advisory.py tests\test_coin_manager_topup_fail_closed.py tests\test_plan_03_17_topup_worker_integration.py tests\test_topup_empty_first.py tests\test_topup_budget_empty_tier_bypass.py tests\test_topup_budget_autoscale.py tests\test_pool_rebuild_respects_tier_target.py tests\test_tier_sizes_mojos_reverse_buy.py tests\test_plan_03_08_requote_flow_integration.py tests\test_plan_02_24_amm_monitor_mempool_watcher_unit.py tests\test_sniper_coin_ids.py tests\test_plan_02_26_sniper_unit.py tests\test_frontend_diagnostics_layout.py tests\test_plan_02_09_market_intel_unit.py
302 passed, 3 subtests passed
```

The targeted batch emitted some intentional fixture warnings/errors while
testing failure paths; the process exit code was successful.

Full suite:

```text
cd tests
python -m pytest -q
2837 passed, 12 skipped, 3 warnings, 42 subtests passed
```

Finish checks:

| Command | Result |
|---|---|
| `python -m py_compile src\catalyst\bot_loop.py tests\test_plan_02_01_bot_loop_unit.py tests\test_full_app_scenario_matrix.py` | passed |
| `python -m ruff check src\catalyst\bot_loop.py tests\test_plan_02_01_bot_loop_unit.py tests\test_full_app_scenario_matrix.py` | passed |
| `git diff --check` | passed; CRLF notices only |
| `python build.py --no-clean` | build successful; `dist\Catalyst\Catalyst.exe` produced |

## Findings and Follow-Ups

### Follow-Up: Cold Status Endpoint Can Stall

During app restart, `/api/status` occasionally took long enough to time out on a
first cold probe, while the root page responded and later status calls worked.
This looks like startup-time wallet/market work leaking into a status endpoint.
It should get a focused follow-up test so a lightweight health/status route
stays responsive during cold start.

### Follow-Up: Browser Test Harness Should Avoid Manual Gate Bypass

For UI screenshots, the Playwright context manually hid startup gates and called
frontend refresh functions. That is useful for read-only inspection, but it can
leave some dashboard cards in placeholder state if the normal startup selection
flow has not populated all frontend globals. A test helper should complete the
normal startup gate flow, or the UI should expose a safe test hook for "already
configured" runs.

### Follow-Up: Console Encoding for Direct Wallet Probes

Calling the Sage wallet helper directly from a default Windows console can hit a
Unicode encoding error because a helper print includes a Unicode arrow. The app
itself was healthy; this is a developer probe/testability issue.

## Deferred Live Runbook

The next live tests should use a pre-filled run sheet per scenario:

1. Record pre-state: active offers, pending cancels, spare pools, alerts, latest
   logs, Tibet/Dexie price.
2. User performs the external-wallet action.
3. Capture first detection timestamp, first protective action timestamp, cancel
   settle timestamp, rebuild timestamp, and final 23/23 or reduced-ladder state.
4. Verify backend events, frontend log wording, dashboard cards, and guidance.
5. Stop if pending cancels do not settle, if offers drop below the expected
   reduced-ladder target, or if guidance recommends Coin Prep when live topup or
   a simple funds top-up is the correct next action.

Priority deferred scenarios:

- `PRICE-01`: one clear TibetSwap move.
- `PRICE-04`: two rapid opposite-direction moves.
- `FILL-01`: one bot sell taken.
- `FILL-02`: one bot buy taken.
- `COIN-05`: user adds CAT to wallet and chooses trading/reserve intent.
- `PREP-07`: Coin Prep cancellation confirmation before combining CAT.
