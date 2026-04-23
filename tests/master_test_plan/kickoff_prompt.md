# Kickoff prompt for a new session

Paste the block below (inside the fence) into a fresh Claude Code
session. The receiving session has everything it needs — it reads the
README + INDEX + any handoff file itself and picks up work.

---

```
You are continuing a distributed comprehensive audit of the CATalyst
CATalyst bot. Work is split into ~106 self-contained slices
across 5 layers (static analysis, unit tests, integration, API
contracts, UI smoke). You own exactly ONE slice this session.

BEFORE ANY OTHER WORK:

1. Read tests/master_test_plan/README.md end to end. That's the full
   workflow contract.

2. Check tests/master_test_plan/handoffs/ for any file — if one exists
   with "wip" status in MASTER_INDEX.md, RESUME that slice instead of
   picking a new one.

3. Otherwise open tests/master_test_plan/MASTER_INDEX.md, pick the
   first `[ ]` pending slice, mark it `[~]`, commit that status change
   as a separate tiny commit, then open the slice folder and start
   work.

WORKFLOW (strict):
  * Default model: Sonnet. Escalate to Opus via the Agent tool with
    model="opus" ONLY for: (a) multi-file bugs you can't untangle,
    (b) ambiguous "is this intended?" questions, (c) architectural
    decisions. One Opus call, not a whole session.
  * Per-slice workflow is documented in the README. Don't deviate.
  * Every fix needs: regression test + pytest green + structured
    commit ("fix(plan NN-MM): <what>") + entry in fixes.md.
  * Out-of-scope issues → spawn_queue.md. Don't chase them this
    session.
  * pytest in tests/ must stay green before every commit.

CONTEXT-EXHAUSTION HANDLING:
  * Monitor your context. Stop when: usage >~70%, quality drops,
    re-reading files 3+ times, >30 min on one slice, or hitting a
    truly ambiguous decision that needs user input.
  * On stop, write tests/master_test_plan/handoffs/YYYY-MM-DD-
    <slice-id>.md using the handoff template, commit all pending work
    as `wip(plan NN-MM): ...`, and output a new-session prompt for the
    user (or paste it yourself in a fresh session — your call).

SUCCESS SIGNAL:
  * One slice moved `[ ]` → `[x]` (or clean handoff on the way to
    done)
  * Full pytest suite green
  * One commit per logical step
  * Zero scope creep

Start now. Read the README first.
```

---

## Tips for the first session

The first time you run this, expect:

1. **Bootstrap friction** — you may want to install `ruff`, `bandit`,
   `vulture`, `radon` in the venv before the static layer. A single
   pip-install commit at the top of layer 01 is fine.

2. **Template drift** — if you find yourself wanting a different
   template shape, update `_templates/` and note the change in the
   session log. Future sessions use the updated one.

3. **Slice size sanity-check** — after slice 1, look back: did it take
   30 min? If it took 15, combine next two; if it took 90, split. The
   slice list is a first draft.

4. **Opus escalation sparingly** — the first 20-30 slices in layers 1
   and 2 almost never need Opus. Don't burn tokens on it. Reserve for
   when Sonnet says "I'm stuck" or "I'm not sure".

## Resumption prompt (after a handoff)

Same as the kickoff — the session reads `handoffs/` as step 2 and
picks up automatically. You don't need a different prompt.

## Minimal prompt (if you only want to check progress)

```
Summarize the current state of tests/master_test_plan/: how many slices
done, in progress, blocked. Read MASTER_INDEX.md. Don't start any new
work. Under 150 words.
```
