# Full-App QA Execution Plan - 2026-05-02

This plan executes the scenario matrix in `docs/testing/full_app_scenario_matrix.md`
from safest to riskiest. The goal is to prove the complete user-visible chain:
trigger, backend decision, wallet/Dexie/Sage state, dashboard state, frontend log,
and guidance recommendation.

## Guardrails

- Do not make external-wallet trades in automated testing. Save TibetSwap/drift
  and taken-offer scenarios that need a separate wallet for the user-led live
  runbook.
- Use the current live Sage offers as a restart/resume fixture while DB and Sage
  agree on the active book.
- Do not cancel all offers unless the scenario specifically requires it and the
  current state has been captured first.
- Prefer atomic tests before live tests. Live tests validate timing and external
  service behavior, not basic business rules.
- Record evidence for every live-safe run: command/API used, expected result,
  actual result, and follow-up defect if the result is wrong.

## Batch 1 - Baseline State Capture

1. Capture git status and active processes.
2. Confirm Catalyst API is stopped or healthy before launching another instance.
3. Query Sage RPC directly for active offers.
4. Query the Catalyst DB for open offers, coin buckets, recent events, and
   health state.
5. Verify DB open offers match Sage fillable offers by side and count.

Exit criteria: current state is safe to use as a restart/resume fixture, or the
fixture is rejected and a controlled cleanup scenario is planned.

## Batch 2 - Atomic and Integration Coverage

1. Validate the scenario matrix file itself stays machine-checkable.
2. Run settings/mode tests:
   - two-sided smart settings
   - buy-only mode
   - sell-only mode
   - mode switch while running
3. Run coin-prep and coin-topup tests:
   - cancel confirmation before CAT combine
   - topup pool reserve protection
   - topup priority below offer rebuild when spare coins are enough
   - reduced ladder behavior when coins/funds are low
4. Run price/requote tests:
   - TibetSwap confirmed move direction
   - one-sided protection mapping from trade asset side
   - pending-cancel settle guard
   - sniper TTL and cleanup
5. Run log/guidance tests:
   - positive action logs show as info/success
   - repeated warnings are rate-limited
   - coin prep is only suggested when it is the correct nuclear option
   - topup-funds recommendation fires when spare CAT is exhausted.

Exit criteria: high-risk scenarios have either passing tests or a documented
gap tied to a new test/defect.

## Batch 3 - API and Dashboard Contract

1. Launch the app in browser-only Flask mode.
2. Confirm startup does not duplicate offers or close Sage.
3. Poll status, alerts, coins, dashboard, logs, and market-intel endpoints.
4. Verify user-facing values use percent where appropriate, not bps.
5. Verify frontend logs do not show scary warnings for intentional churn.
6. Verify dashboard cards and chart placeholders are truthful during startup.
7. Capture screenshots for Offers, Market Intelligence, Wallet, Logs, and
   Guidance after the API is healthy.

Exit criteria: the dashboard accurately represents the current DB/Sage state and
the log stream is helpful, not alarming.

## Batch 4 - Live-Safe Operational Tests

1. Restart/resume against the current 23/23 live book.
2. Start and stop the app without closing Sage.
3. Trigger coin manager refreshes that do not require external trades.
4. Validate incoming unallocated CAT handling with read-only evidence if such a
   deposit is already present.
5. Validate shutdown leaves Sage running and active offers untouched unless the
   user explicitly requests cancellation.

Exit criteria: no offer churn, duplicate creation, false coin-prep advice, or
Sage lifecycle regression during ordinary app use.

## Batch 5 - Deferred User-Led Live Runbook

These scenarios are intentionally saved for the user because they need an
external wallet, market activity, or real funds movement:

- `PRICE-01` through `PRICE-06`: TibetSwap shocks and whipsaws.
- `FILL-01` through `FILL-07`: taken offers and fill recovery.
- `COIN-02`, `COIN-05`, `COIN-06`: real incoming funds and topup pool changes.
- Any scenario requiring all live offers to be cancelled before coin prep.

Before running these, each scenario must have a timestamped run sheet with:
pre-state, action to take, expected log events, expected dashboard changes,
settle condition, and abort criteria.

## Evidence Output

Create run notes under `docs/testing/runs/` as testing proceeds. Each note should
be concise and factual:

- scenario IDs covered
- commands/API endpoints used
- observed counts and timestamps
- pass/fail/partial result
- defects opened or tests added
