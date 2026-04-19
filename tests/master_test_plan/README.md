# Master Test Plan — Workflow

A distributed comprehensive audit of the CATalyst Chia Market Maker bot,
built to be worked through across many short sessions with full context
fidelity.

## The big picture

The plan is a **five-layer pyramid**, ordered cheapest→slowest:

1. **Static analysis** — lint, security, dead code, complexity (fast, broad)
2. **Unit tests** — expand from current 506 toward ~1,500 covering every module
3. **Integration** — end-to-end flows with mocked externals
4. **API contracts** — every `/api/*` endpoint × happy + error + edge
5. **UI smoke** — every tab, every button, every modal (slowest, narrowest)

Each layer is broken into **slices** of ~30 min each. A slice is the
contract a single session commits to finishing. A session never owns
more than one slice.

## The single source of truth

**[MASTER_INDEX.md](MASTER_INDEX.md)** — every slice listed with status
(`[ ] pending` / `[~] in-progress` / `[x] done`), owner session, commit
hash. Always update this file when a slice changes state.

## Per-slice workflow

```
1. Open MASTER_INDEX.md, pick the first [ ] pending slice.
2. Mark it [~] in-progress in MASTER_INDEX.md (commit separately).
3. Open the slice's folder: layers/<NN_layer>/<slice-id>/
4. Read plan.md (pre-written enumeration of what to check).
5. Execute the plan:
   a. For each item, RUN the test (pytest / curl / DOM eval / grep).
   b. Log every FAIL in findings.md with: reproduction + severity.
   c. For each fixable fault:
      - Minimal reproduction → isolate root cause
      - Fix the underlying code
      - Add a regression test (pytest) that fails before + passes after
      - Run the relevant pytest subset — ZERO regressions before next fix
      - Log in fixes.md with: commit hash, regression-test path
   d. For out-of-scope issues (bugs in a different module): append to
      spawn_queue.md for a future slice. Don't chase mid-slice.
6. When all plan items processed:
   - Full pytest suite pass (506+ currently) — must stay green
   - Commit with: "test(plan <slice-id>): <summary>"
   - Update MASTER_INDEX.md: [~] → [x] + commit hash (separate commit)
7. Stop. Don't start another slice.
```

## Escalation to Opus

**Default model: Sonnet.** Keep it cheap and grind-fast.

**Escalate to Opus** (via the `Agent` tool, `model: "opus"`) when:

- A bug's root cause spans 3+ files and you can't see the pattern
- A fix needs architectural reasoning (e.g. "should this live in X or Y?")
- A test surfaces ambiguous behaviour — is this intended or a bug?
- You've gone 2+ rounds of a fix and it keeps breaking other things
- The plan enumeration itself is unclear for a complex state machine
  (coin_manager, offer_manager, risk_manager)

Escalation is **one call**, not a whole Opus session. Brief the Opus
sub-agent with the concrete question + relevant context. It reports
back with a recommendation. Parent session decides whether to implement
the recommendation or flag the slice as blocked.

## Context-exhaustion handling

A session **monitors its own context**. Stop when ANY of these trip:

- Context window usage visibly climbing past ~70% (use judgement; the
  harness surfaces approximate context pressure)
- Response quality dropping (e.g. mis-remembering file contents,
  forgetting what slice you're on)
- Having to re-read the same file 3+ times
- More than 30 min elapsed on a single slice

When any condition trips, go into **graceful handoff mode**:

```
1. DO NOT start any new work.
2. Commit all pending code changes with a clear "wip: <slice-id>" prefix.
3. Write handoffs/<YYYY-MM-DD>-<slice-id>.md from the template.
   Include: what was done, what's left, any open decisions, next step.
4. In MASTER_INDEX.md, add a note next to the slice: "wip — see
   handoffs/<file>.md".
5. Output a new-session kickoff prompt to the user (see template below).
6. Stop.
```

**Picking up a handoff** (opposite direction): when starting a session,
check `handoffs/` for any slice marked wip. If found, resume it before
picking a new pending slice.

## Commit message format

Consistent shape so the history is searchable:

```
test(plan <slice-id>): <one-line summary of what the slice verified>

- Checks completed: N / M
- Issues found: K  (see findings.md)
- Fixes landed: J  (see fixes.md)
- Spawned out-of-scope items: L  (see spawn_queue.md)
- Regression tests added: <path1>, <path2>

Co-Authored-By: Claude ...
```

When fixing a fault mid-slice, commit the fix separately BEFORE the
summary commit:

```
fix(plan <slice-id>): <concrete description>
```

## Files in each slice folder

Every slice folder has the same shape (copy from `_templates/`):

```
layers/NN_layer/<slice-id>/
  plan.md          ← what to check (often pre-written)
  findings.md      ← what failed (one entry per fault)
  fixes.md         ← what was fixed + regression test path
  spawn_queue.md   ← out-of-scope items flagged for later
```

When opening a new slice, copy all four templates if any are missing.

## Safety rails

**Never** modify these without explicit user approval:
- `.env` files (real wallet config)
- Anything in `backups_pre_audit_cleanup_*`
- Anything in `dist2/` (built artifacts)

**Never** run live trading in a test:
- Coin prep tests against a real Sage-connected wallet must check
  `cfg.DRY_RUN == True` OR be gated behind a `@live_trading_test`
  marker that's skipped by default
- API tests should hit stubs, not `localhost:5000` on a running bot,
  unless the slice explicitly says "live"

**Never** commit code that breaks the suite:
- `pytest -q` in the `tests/` directory must pass green before every
  commit. If it doesn't, fix it or revert — don't stack more on top.

## Kickoff prompt for a new session

Paste this into a new Claude Code session to start or resume work:

```
You are continuing the master test plan audit for the CATalyst bot.

1. Read `tests/master_test_plan/README.md` end to end. This is your
   full workflow brief.
2. Check `tests/master_test_plan/handoffs/` — if any file exists and
   points to an unfinished slice, resume that slice first.
3. Otherwise open `tests/master_test_plan/MASTER_INDEX.md`, pick the
   first `[ ] pending` slice, mark it `[~]`, and follow the per-slice
   workflow exactly.
4. When done (or handoff triggered), stop. Do not start another slice.
5. Default to Sonnet. Use `Agent` with `model: "opus"` for escalation
   only (see README for criteria).

Your success signal: one slice moved `[ ] → [x]` (or clean handoff),
full pytest green, one commit per logical step, no scope creep.
```

## Estimated scale

- Layer 1: 8 slices × ~30 min = 4 hours
- Layer 2: 32 slices × ~45 min = 24 hours
- Layer 3: 18 slices × ~45 min = 13.5 hours
- Layer 4: 22 slices × ~30 min = 11 hours
- Layer 5: 26 slices × ~45 min = 19.5 hours

**Total: ~106 slices, ~72 person-hours.** At 2 slices per session, that's
~53 sessions. At 2-3 sessions/day, 3-4 weeks of elapsed time.

Critically: the pyramid is **strictly monotonic-improving**. You can
stop at any slice and be better off than when you started. Layer 1 and
2 alone will surface 80% of real bugs.
