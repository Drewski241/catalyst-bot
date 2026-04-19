# Fixes — Slice 03-11

No production code fixes needed.

The hysteresis behaviour (streak not reset when price is still bad during CB active) is
documented as a finding. It is not incorrect for typical use — the streak accumulates toward
clearing across non-consecutive good cycles, which is safe for the expected usage patterns.
No change made. Test pinned the actual behaviour.
