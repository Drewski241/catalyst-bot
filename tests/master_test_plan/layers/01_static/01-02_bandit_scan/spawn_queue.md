# Spawn queue — Slice 01-02

Out-of-scope issues found during this slice.

---

## Queue

- [ ] **wallet_sage.py SSL context — consider proper CA verification** — `wallet_sage.py`
  uses `ssl._create_unverified_context()` for the Sage RPC connection. Same as
  tx_fees.py before the fix — Sage might expose its own CA cert at a predictable
  path for proper TLS verification.
  - Discovered at: `wallet_sage.py:360, 401` (B323 finding)
  - Why out-of-scope here: Sage CA cert path investigation needed; out of bandit-scope
  - Severity: low (localhost only, mutual TLS for auth)
  - Suggested slice: 01-05 (type annotation audit) or dedicated security hardening slice

- [ ] **1361 LOW-severity bandit findings not reviewed** — bandit LOW severity
  includes things like `hashlib.md5` usage, random number generation, etc. None
  are critical for a localhost trading bot but worth a one-pass triage.
  - Discovered at: bandit scan output
  - Why out-of-scope here: 1361 findings; needs a full dedicated session
  - Severity: low
  - Suggested slice: add new slice 01-09 "bandit LOW findings triage"

---

## Dispatched

(none yet)
