# Handoff — <YYYY-MM-DD> — Slice <SLICE-ID>

**Reason for handoff:** <context climbing past 70% / quality dropping /
ambiguous decision / time budget exceeded — pick one>

## What was done this session

- <bullet>
- <bullet>

Commits landed (including WIP):
- `<hash>` <subject>
- `<hash>` <subject>

## What is left on this slice

Pending checks (copy status from plan.md):

- [ ] 1.2
- [ ] 2.1
- [ ] 2.2

## Open decisions / ambiguities

Any question the next session needs to answer before proceeding. E.g.:

- Is it intended that `<function>` returns `None` on <input>, or should it
  raise? (see check 2.1 in plan.md)
- The fix for F1 may affect slice 03-09; should we hold until that
  slice owner decides?

## Next immediate step

One concrete action the next session should take. _"Re-run
`pytest -k test_price_engine::test_weighted_fallback` to reproduce F2,
then decide whether to fix in this module or push to risk_manager."_

## Prompt for new session

Paste verbatim:

```
Resume master test plan work. Start by reading
tests/master_test_plan/handoffs/<YYYY-MM-DD-slice-id>.md — the previous
session hit <reason> mid-slice and left notes. Finish slice <SLICE-ID>
before picking any new pending slice. Default to Sonnet; escalate to
Opus via Agent tool if you hit the same block the previous session did.
Follow tests/master_test_plan/README.md workflow exactly.
```
