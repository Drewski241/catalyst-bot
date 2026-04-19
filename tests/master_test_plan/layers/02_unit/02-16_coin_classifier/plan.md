# Slice 02-16: coin_classifier.py unit tests

**Layer:** 2 · **Estimated time:** 45 min · **Escalate to Opus if:** a
check reveals the classifier disagrees with itself between call sites.

## Goal

Comprehensively unit-test `coin_classifier.py` — the single source of
truth for "which tier does this coin fit?" Its correctness drives F70
misfit rejection, coin prep designation, and the offer selector.

## Scope

### In-scope
- `coin_classifier.py` — every public function
  - `classify_coin(amount_mojos, tier_sizes_mojos, **opts)`
  - `is_misfit_coin(...)`
  - `infer_designation_by_size(...)`
  - `CoinFit` enum boundary cases

### Out-of-scope
- `coin_manager.get_tier_sizes_mojos_from_cfg()` — covered by slice 02-14
- Anywhere the classifier is *called* from — that's covered by the caller's slice

## Checks

### 1. Exact tier fit
- [ ] **1.1** Coin at exact tier size returns `CoinFit.EXACT` for that tier
- [ ] **1.2** Coin at 0.98× tier size returns `EXACT` (floor tolerance)
- [ ] **1.3** Coin at 0.97× returns `UNDER_FLOOR` for that tier (just below floor)
- [ ] **1.4** Coin at 1.00× returns `EXACT` (top of range)
- [ ] **1.5** Coin at 1.50× returns `OVERSIZE_FIT` (at ceiling)
- [ ] **1.6** Coin at 1.51× returns `OVER_CEILING`

### 2. Best-tier selection across multiple tiers
- [ ] **2.1** Given tiers {inner:2.0, mid:1.0, outer:0.5, extreme:0.25}, a 1.0 coin picks "mid" (exact)
- [ ] **2.2** A 1.05 coin in same dict prefers "mid" EXACT over "outer" OVERSIZE_FIT
- [ ] **2.3** A 0.6 coin prefers "outer" EXACT over "mid" UNDER_FLOOR
- [ ] **2.4** Tied exact matches pick the smaller tier (comment in source says so)

### 3. Dust and reserve categories
- [ ] **3.1** Coin at 0.5× smallest-tier is DUST (designation), `best_tier=None`, `is_misfit=False`
- [ ] **3.2** Coin at 0.49× smallest is DUST (boundary)
- [ ] **3.3** Coin at 2.0× largest-tier is RESERVE, `best_tier=None`, `is_misfit=False`
- [ ] **3.4** Coin at 1.99× largest is neither (goes through the tier loop and becomes OVER_CEILING misfit OR tier-fit — verify which)

### 4. Misfit detection
- [ ] **4.1** A coin above inner ceiling AND below everything else returns is_misfit=True
- [ ] **4.2** A coin between mid and outer that fits neither (tight bounds) is misfit
- [ ] **4.3** `is_misfit_coin()` convenience helper matches `classify_coin().is_misfit`

### 5. Edge inputs
- [ ] **5.1** `amount_mojos=0` returns UNKNOWN + is_misfit=True
- [ ] **5.2** `amount_mojos=-1` same
- [ ] **5.3** Empty `tier_sizes_mojos={}` returns UNKNOWN + is_misfit=True
- [ ] **5.4** `tier_sizes_mojos={"inner": 0}` — zero tier is filtered silently
- [ ] **5.5** Nested Decimal/int types all handled (mojos can be either)

### 6. Custom thresholds
- [ ] **6.1** Passing `floor_tolerance=0.9` relaxes the UNDER_FLOOR boundary — verify a 0.91 coin now EXACT
- [ ] **6.2** `max_ratio=2.0` extends OVERSIZE_FIT range
- [ ] **6.3** `dust_fraction=0.1` lets tinier coins qualify
- [ ] **6.4** `reserve_multiple=3.0` raises the reserve threshold
- [ ] **6.5** `max_size_ratio=float('inf')` in `is_misfit_coin()` — never rejects for being too big

### 7. Contract guarantees (invariants from module docstring)
- [ ] **7.1** When `fit` is EXACT or OVERSIZE_FIT, `best_tier` is non-None
- [ ] **7.2** `nearest_tier` is populated whenever ≥1 tier is defined
- [ ] **7.3** `designation` is one of the `CoinDesignation` enum values

### 8. Backward-compat wrappers
- [ ] **8.1** `infer_designation_by_size()` returns `("dust", "none")` for dust
- [ ] **8.2** Same, `("reserve", "none")` for reserve
- [ ] **8.3** Same, `("tier_spare", "<tier>")` for a fit
- [ ] **8.4** Same, `("unknown", "none")` for misfit

## Execution notes

```bash
cd tests && python -m pytest test_coin_classifier.py -v
```

Write new tests in `tests/test_coin_classifier.py` (create if missing).
Use parametrised tests for boundary cases — don't hand-roll 20 separate
test functions.

## Success criteria

- All 38 checks above have corresponding pytest cases (green)
- `pytest -q` total increases by ~20-30
- Zero regressions in the existing suite
- If any check reveals inconsistent behaviour → add a finding, escalate
  to Opus for "is this a bug or is my expectation wrong?"
