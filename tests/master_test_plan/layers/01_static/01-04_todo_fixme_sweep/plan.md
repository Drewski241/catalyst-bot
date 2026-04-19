# Slice 01-04: TODO / FIXME / XXX sweep

**Layer:** 1 · **Estimated time:** 30 min · **Escalate to Opus if:**
a TODO describes a design decision that needs architectural input.

## Goal

Find every TODO / FIXME / XXX / HACK comment in the codebase, triage
into (a) resolved but comment left behind, (b) real future work, (c)
real current bugs. Clear (a), file (c) as findings, append (b) to a
persistent tech-debt log.

## Scope

### In-scope
- All `*.py`, `*.html`, `*.md` at repo root + tests/
- Patterns: `TODO`, `FIXME`, `XXX`, `HACK`, `NOTE:` (case-insensitive)

### Out-of-scope
- Third-party libs
- `backups_pre_audit_cleanup_*`, `dist2/`, `dist/`

## Checks

### 1. Collection
- [ ] **1.1** Run `grep -rniE "(TODO|FIXME|XXX|HACK)[:\s]" --include="*.py" --include="*.html" .` (exclude backups + dist)
- [ ] **1.2** Count total, list top 10 files by frequency
- [ ] **1.3** Save the raw list to findings.md as an appendix

### 2. Triage
For each comment, categorise:
- [ ] **2.1** **Resolved-but-stale**: the comment references work that's already done. Delete the comment in a single cleanup commit.
- [ ] **2.2** **Real future work**: move to `docs/tech_debt.md` (create if missing) with file:line reference + brief context.
- [ ] **2.3** **Real current bug**: file as a finding in this slice's findings.md + either fix now (if small) or spawn-queue for the module's own slice.
- [ ] **2.4** **Legitimate explanation note**: leave in place. Flag if the wording is misleading (should be NOTE not TODO).

### 3. Cleanup commit
- [ ] **3.1** Single commit `chore(plan 01-04): remove stale TODO/FIXME comments (N)` for the resolved-but-stale set.
- [ ] **3.2** `pytest -q` green before commit.
- [ ] **3.3** Separate commit for `docs/tech_debt.md` seeding if needed.

## Execution notes

```bash
# Collection
grep -rniE "(TODO|FIXME|XXX|HACK)[:\s]" \
  --include="*.py" --include="*.html" \
  --exclude-dir=backups_pre_audit_cleanup_20260408 \
  --exclude-dir=dist --exclude-dir=dist2 \
  . > /tmp/todos.txt
wc -l /tmp/todos.txt

# Frequency by file
awk -F: '{print $1}' /tmp/todos.txt | sort | uniq -c | sort -rn | head -10
```

## Success criteria

- All stale comments removed
- All real bugs either fixed or logged
- `docs/tech_debt.md` exists with a curated list of real future work
  (not every old comment copied verbatim)
