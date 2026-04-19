# Findings — Slice 01-02

Baseline: HIGH=3 (1 real + 2 bandit duplicate-count bug), MEDIUM=77 (all FP), LOW=1361.
After fix + .bandit config: HIGH=0, MEDIUM=0.

---

## Finding F1: tx_fees._full_node_rpc uses verify=False unconditionally

**Check:** 2.1 · **Severity:** high · **Status:** fixed

### Reproduction
```
bandit tx_fees.py  →  B501 HIGH: verify=False in requests.post at _full_node_rpc
```

### Root cause
`_full_node_rpc` (tx_fees.py) hardcoded `verify=False` for all Chia full-node
RPC calls. Chia RPC uses a per-installation private CA — when available, TLS
server identity can be verified against `ssl/ca/private_ca.crt`. The original
code skipped this entirely. MITM risk is low on localhost but proper
verification is achievable and preferred.

### Resolution
- [x] Fix committed: 2968308
- [x] New helper `_get_chia_ca_cert()` returns CA cert path or None
- [x] `_full_node_rpc` passes `verify=ca_cert` when CA exists, `verify=False` as fallback
- [x] Regression test: `tests/test_plan_01_02_bandit_fixes.py::TestTxFeesFullNodeRpcTLS`
- [x] No regressions in `pytest -q`

---

## Finding FP1: B501 duplicate — bandit bug in directory scan

**Check:** 1.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
`bandit -r .` reports 3 B501 HIGH findings for tx_fees.py but running
`bandit tx_fees.py` directly reports only 1. This is a known bandit
duplicate-reporting quirk when scanning directories — the same multi-line
`requests.post(...)` call is counted multiple times. After the F1 fix,
running `bandit tx_fees.py` directly returns 0 HIGH findings.

---

## Finding FP2: B608 (38) — parameterized SQL flagged as injection

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
All 38 B608 findings use parameterized `?` placeholders. Dynamic portions
(`where_clause`, `col_list`, `placeholders`, `updates`) are composed of
hardcoded strings or DB schema metadata, never raw user input. Reviewed in
database.py, api_server.py, coin_manager.py. Suppressed in `.bandit`.

---

## Finding FP3: B310 (24) — urllib.request.urlopen with localhost URLs

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
All calls target hardcoded localhost URLs (Flask at 127.0.0.1:5000,
Sage at localhost:9257, Chia at localhost:8555). No user-controlled URLs.
Suppressed in `.bandit`.

---

## Finding FP4: B323 (8) — ssl._create_unverified_context

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
Intentional: Sage and Chia wallet RPCs use self-signed certs on localhost.
`ssl._create_unverified_context()` is the standard approach for all Chia
ecosystem clients. wallet_sage.py and test files. Suppressed in `.bandit`.

---

## Finding FP5: B104 (4) — 0.0.0.0 binding detection

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
`splash_node.py` detects `0.0.0.0` and REPLACES it with `127.0.0.1`.
The code prevents dangerous binding, not causes it. One P2P listener
intentionally uses all interfaces for blockchain node operation.
Suppressed in `.bandit`.

---

## Finding FP6: B102 (2) — exec in test isolation helper

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
`test_bot_loop_sage_status_mapping.py` uses `exec(compile(...))` to run
module code in isolation, preventing import side-effects during testing.
Not in production paths. Suppressed in `.bandit`.

---

## Finding FP7: B113 (1) — requests no timeout (false detection)

**Check:** 3.1 · **Severity:** n/a · **Status:** documented false positive

### Notes
Bandit flags the `timeout = getattr(cfg, "COINSET_TIMEOUT", 5)` line in
`coinset_client.py`, NOT the `requests.post()` call. All calls verified
to have `timeout=timeout`. Suppressed in `.bandit`.

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open |
| 1 | fixed |
| 7 | documented FP |
| 0 | blocked |
