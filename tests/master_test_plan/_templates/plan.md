# Slice <SLICE-ID>: <TITLE>

**Layer:** <1-5> · **Estimated time:** <20-60 min> · **Escalate to Opus if:** <trigger>

## Goal

One-sentence statement of what this slice verifies. E.g. _"Confirm every
branch of `price_engine.get_weighted_price()` produces a valid Decimal
for the expected input ranges."_

## Scope

### In-scope
- Files: `<file1.py>`, `<file2.py>`
- Functions / endpoints / views: `<name1>`, `<name2>`

### Out-of-scope
- Anything requiring live Sage RPC (use stubs)
- Refactors that touch more than 1 file
- Performance tuning

## Checks

Each check is a distinct verification. Numbered so `findings.md` can
reference them ("fails check 3.2").

### <Category 1>
- [ ] **1.1** <specific check — e.g. "returns Decimal for valid (bid, ask)">
- [ ] **1.2** <specific check — e.g. "raises ValueError when bid > ask">
- [ ] **1.3** <specific check>

### <Category 2>
- [ ] **2.1** <specific check>
- [ ] **2.2** <specific check>

## Execution notes

Commands to run, fixture setup needed, environment preconditions.

```bash
# e.g.
cd tests && python -m pytest -k "test_price_engine" -v
```

## Success criteria

- All `[ ]` checks either `[x]` passed or have an entry in findings.md
- `pytest -q` in tests/ still green (506+ passing)
- Any fault found is either fixed OR logged in findings.md as blocked
