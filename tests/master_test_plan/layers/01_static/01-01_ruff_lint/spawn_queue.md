# Spawn queue — Slice 01-01

Out-of-scope issues found during this slice.

---

## Queue

- [ ] **B007: 28 loop variables not used in loop body** — `for x in ...: ...` where `x`
  is not referenced inside the loop. Often intentional (counting iterations) but
  worth verifying the variable isn't accidentally shadowed or forgotten.
  - Discovered at: `ruff check .` with B rules, 28 occurrences across multiple files
  - Why out-of-scope here: requires per-occurrence review of intent; doesn't
    affect correctness by itself
  - Severity: low
  - Suggested slice: 01-03 (dead code sweep) — review alongside vulture output

- [ ] **F841: 18 unused local variables (non-auto-fixable)** — assigned once, never
  read. Most are `result = some_call()` where the return value is ignored.
  Some may indicate missed error-handling.
  - Discovered at: `ruff check .` post-fix, F841 rule
  - Why out-of-scope here: needs manual triage; some are intentional (side-effect
    calls), some are missed error handling
  - Severity: medium
  - Suggested slice: 01-03 (dead code sweep)

- [ ] **noqa directive format error in tests/test_parallel_offers.py:166** — ruff warns
  `Invalid # noqa directive: expected comma-separated list of codes`. The noqa
  comment has wrong syntax and silences nothing.
  - Discovered at: `tests/test_parallel_offers.py:166`
  - Why out-of-scope here: test-only noise, no production impact
  - Severity: low
  - Suggested slice: fix inline when touching test_parallel_offers.py

- [ ] **E712: 3 comparison-to-True/False** — `if x == True:` instead of `if x:`.
  Flags in api_server.py and bot_loop.py. In rare cases (comparing actual bool
  columns from SQLite rows) the explicit form is intentional.
  - Discovered at: `ruff check .` E712 rule
  - Why out-of-scope here: need to verify each is not deliberately checking type
  - Severity: low
  - Suggested slice: 01-05 (type annotation audit) — review alongside mypy output

---

## Dispatched

(none yet)
