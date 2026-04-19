# Slice 04-01: status endpoints contract

**Layer:** 4 · **Estimated time:** 30 min · **Escalate to Opus if:** a
response shape regresses because of upstream dependency change (bot
instance missing, wallet down, etc.) in ways the contract can't express.

## Goal

Verify the three primary "read bot state" endpoints return JSON matching
a documented shape across the states the bot can be in (idle / starting
/ running / blocked / stopped).

## Endpoints covered

- `GET /api/status` — top-level aggregated state
- `GET /api/bot/state` — simpler running/stopped flag + stats
- `GET /api/bot/price` — live pricing snapshot

## Scope

### In-scope
- HTTP status code is 200 in every normal case
- JSON parses
- Required keys present (see shape)
- Value types match (bool/int/string/Decimal-as-string/Dict/List)
- `liquidity` sub-block on `/api/status` (added 2026-04-19)

### Out-of-scope
- Performance / latency (separate slice if desired)
- Content correctness beyond "shape matches" (that's layer 2/3 territory)

## Checks

### 1. /api/status shape
- [ ] **1.1** Returns 200 with `application/json` content type
- [ ] **1.2** Top-level keys: `running`, `wallet_type`, `balances`, `chia_health`, `diagnostics`, `current_cat`, `liquidity`, `stats` (non-exhaustive — check the shape matches)
- [ ] **1.3** `running` is bool
- [ ] **1.4** `balances.xch` has `spendable`, `total` as numbers; `balances.cat` same
- [ ] **1.5** `chia_health.status` is one of `healthy`, `degraded`, `unreachable`
- [ ] **1.6** `diagnostics.active_conditions` is a list
- [ ] **1.7** `liquidity.mode` is one of `two_sided`, `buy_only`, `sell_only`
- [ ] **1.8** `liquidity.active_side` matches mode semantically (both/buy/sell)
- [ ] **1.9** `liquidity.parked` is bool
- [ ] **1.10** When `parked==true`, `parked_reason` + `parked_message` are strings
- [ ] **1.11** `stats` has `uptime_seconds`, `loop_count`, `total_fills`, `errors`

### 2. /api/bot/state shape
- [ ] **2.1** Returns 200
- [ ] **2.2** Fields present: (inspect the source — `api_server.py::api_bot_state`, document in findings.md)
- [ ] **2.3** Idempotent — two calls return identical payloads (within 1s clock skew)

### 3. /api/bot/price shape
- [ ] **3.1** Returns 200 when a trading pair is selected
- [ ] **3.2** Has `mid`, `bid`, `ask` (at least) as strings (Decimal-serialised) or numbers
- [ ] **3.3** When no pair selected, returns error payload (not a 500)

### 4. Error handling
- [ ] **4.1** When `bot` global is `None` (mid-init), `/api/status` doesn't 500 — returns partial payload
- [ ] **4.2** When wallet is unreachable, `chia_health.status != "healthy"` and callers can distinguish
- [ ] **4.3** Unknown query params are ignored, not rejected

### 5. Caching / freshness
- [ ] **5.1** `/api/status` always serves fresh (no stale response cached past ~1s)
- [ ] **5.2** No `Cache-Control: public` header on these endpoints

## Execution notes

Prefer direct curl/fetch against a running --flask instance on 5000:

```bash
curl -sf http://127.0.0.1:5000/api/status | jq 'keys'
curl -sf http://127.0.0.1:5000/api/bot/state | jq .
curl -sf http://127.0.0.1:5000/api/bot/price | jq .
```

If the suite is shifting to proper API contract tests with a response
schema tool (e.g. `pydantic` models), add them in `tests/test_api_contracts.py`.

## Success criteria

- A documented contract (in this file's findings.md OR a new
  `docs/api_contracts.md`) for each endpoint's response shape
- At least one pytest case per endpoint covering the happy-path shape
- Any discrepancy with what the GUI expects gets logged as a finding
