# Findings — Slice 03-08

Integration tests for the requote flow: offer_manager + reaction_strategy module wiring.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestShouldRequote` | 8 | threshold, cooldown, disabled, zero price, downward move |
| `TestShouldRequoteGraduated` | 9 | all 5 severity levels, cooldown suppression, symmetric drift, disabled |
| `TestSeverityToTierSetWiring` | 5 | inner→inner only, full→all tiers, superset chain, none→empty |
| `TestCustomDriftThresholds` | 3 | cfg-driven thresholds (not hardcoded) verified |

**25 new tests** in `tests/test_plan_03_08_requote_flow_integration.py`.

## No bugs found
