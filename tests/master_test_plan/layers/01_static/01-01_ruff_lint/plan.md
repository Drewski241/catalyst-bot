# Slice 01-01: ruff lint sweep — top findings + auto-fix

**Layer:** 1 · **Estimated time:** 45 min · **Escalate to Opus if:** a
finding is ambiguous about intended behaviour (rare for lint).

## Goal

Run ruff over the entire Python codebase, land every safe auto-fix, and
triage remaining findings into (a) real bugs worth fixing now, (b) style
nits to leave alone, (c) out-of-scope items for the spawn queue.

## Scope

### In-scope
- All `*.py` at the repository root AND in `tests/`
- Auto-fixable issues (run `ruff check --fix`)
- High-severity manual triage items (F-, E9-, B-prefixed rules)

### Out-of-scope
- Files under `backups_pre_audit_cleanup_*`, `dist2/`, `dist/`
- Formatting-only changes (ruff format) — separate slice if desired
- Config bikeshedding — if ruff suggests a config change, log it and
  skip; don't argue with its defaults

## Checks

### 1. Baseline
- [ ] **1.1** Run `ruff check . --exclude backups_pre_audit_cleanup_20260408 --exclude dist --exclude dist2 --output-format=json` and record the total count + per-rule histogram.
- [ ] **1.2** Record the top 10 rules by frequency in findings.md (so the fix pass is prioritised).

### 2. Safe auto-fix
- [ ] **2.1** Run `ruff check --fix` (auto-fix only). Review the diff — it should be mechanical (unused imports, trailing whitespace, etc.).
- [ ] **2.2** Run `pytest -q` in tests/. ZERO regressions before commit.
- [ ] **2.3** Commit with message `fix(plan 01-01): ruff auto-fix pass — <N> findings cleared`.

### 3. Manual triage — high severity only
- [ ] **3.1** List remaining findings for rules starting with `F` (pyflakes), `E9` (syntax), or `B` (bugbear). These are the most likely to be real bugs.
- [ ] **3.2** For each: decide fix-now / spawn-queue / leave.
  - Real bug (e.g. `F811` redefined-while-unused, `B006` mutable default arg): fix + regression test.
  - Style nit in live code: log to spawn_queue.md as low-severity.
  - Test-only noise: either fix or silence with `# noqa:` + short explanation.

### 4. Persist configuration
- [ ] **4.1** If `pyproject.toml` / `ruff.toml` doesn't exist, create one that reflects the final accepted rule set.
- [ ] **4.2** Commit config with message `chore(plan 01-01): add ruff config reflecting audit pass`.

## Execution notes

```bash
# If ruff isn't installed in the venv already:
pip install ruff

# Full scan, JSON output for analysis
ruff check . --exclude backups_pre_audit_cleanup_20260408 --exclude dist --exclude dist2 --output-format=json > /tmp/ruff.json

# Rule histogram
python -c "import json; d=json.load(open('/tmp/ruff.json')); from collections import Counter; c=Counter(r['code'] for r in d); [print(f'{k:10} {v}') for k,v in c.most_common(20)]"

# Safe auto-fix (mechanical only — no breaking changes)
ruff check . --exclude backups_pre_audit_cleanup_20260408 --exclude dist --exclude dist2 --fix
```

## Success criteria

- `ruff check .` returns 0 critical (F9*, E9*, B9*) issues, OR every
  remaining one has a finding entry explaining why it's left
- `pytest -q` still green
- Config file persisted so future runs use the same rule set
