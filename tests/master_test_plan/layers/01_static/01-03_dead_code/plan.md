# Slice 01-03: dead code — vulture + manual unused-function check

**Layer:** 1 · **Estimated time:** 30 min · **Escalate to Opus if:** a function
looks unused but its name suggests it might be a callback, hook, or dynamic
dispatch target.

## Goal

Find functions, classes, and variables that are defined but never called.
Vulture gives a first-pass list; manual inspection confirms or refutes each hit.
Only delete code that is provably unreachable. Anything uncertain goes to
spawn_queue.md.

## Scope

### In-scope
- All `*.py` at repository root AND `tests/`
- Functions, methods, classes, variables with zero references
- Code flagged unused by prior ruff pass (F841 leftovers from spawn queue 01-01)

### Out-of-scope
- `backups_pre_audit_cleanup_*`, `dist2/`, `dist/`
- PyWebView API methods exposed to JS via `window.pywebview.api.*` — these look
  unused from Python's perspective but are called from JavaScript
- Flask route functions — called by the framework, not from Python directly
- pytest fixtures and hook functions — called by pytest infrastructure
- `__all__`, `__version__`, module-level dunder attributes

## Checks

### 1. Vulture baseline
- [ ] **1.1** Run `vulture . --min-confidence 80 --exclude backups_pre_audit_cleanup_20260408,dist,dist2` and record the count.
- [ ] **1.2** Filter out known false-positive categories (Flask routes, PyWebView API methods, pytest fixtures).
- [ ] **1.3** Record remaining suspect items by module.

### 2. Manual triage
- [ ] **2.1** For each remaining item: search for callers with `grep -rn "<name>"`.
  - Zero callers confirmed dead → remove + regression test.
  - Dynamic dispatch (getattr, __dict__, JS bridge) → mark FP, add `# pragma: nocover` or whitelist comment.
  - Uncertain (callback, hook pattern) → spawn-queue.

### 3. F841 from 01-01 spawn queue
- [ ] **3.1** Review the 18 non-auto-fixable F841 (unused local variable assignments) from 01-01.
  - Side-effect calls where result is intentionally ignored → `_ = call()` or `# noqa: F841`
  - Genuine dead assignment → remove.

### 4. vulture whitelist
- [ ] **4.1** Create `vulture_whitelist.py` listing any intentionally-kept but unused names
  (e.g. PyWebView API methods, module-level config constants referenced only at import time).

## Execution notes

```bash
pip install vulture
vulture . --min-confidence 80 --exclude backups_pre_audit_cleanup_20260408,dist,dist2 > /tmp/vulture.txt
wc -l /tmp/vulture.txt

# Filter routes and pywebview methods
grep -v "@app.route\|pywebview\|def test_\|pytest\|fixture" /tmp/vulture.txt | head -60
```

## Success criteria

- All confirmed dead code removed (or whitelisted with explanation)
- `pytest -q` still green
- 18 F841 leftovers resolved
