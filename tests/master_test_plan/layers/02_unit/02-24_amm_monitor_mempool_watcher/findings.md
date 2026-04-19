# Findings — Slice 02-24

Unit tests for `amm_monitor.py` and `mempool_watcher.py`.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `mempool_watcher._encode_amount` | 8 | 0, 1, 127 (no prepend), 128/255 (high-bit prepend), 256, large, type check |
| `mempool_watcher.compute_coin_id` | 6 | returns 64-char hex, deterministic, different amounts differ, invalid hex→"", 0x prefix stripped |
| `AMMMonitor.get_drift_bps` | 7 | no state, no price, no quoted, same price=0bps, 1%=100bps, buy-only, always non-negative |
| `AMMMonitor.get_arb_pressure_label` | 4 | low/moderate/high/critical score bands |
| `AMMMonitor.check_amm_buffer` | 7 | disabled→True, no-state fail-open, buy safe/unsafe, sell safe/unsafe, unavailable fail-open |

**32 new tests** in `tests/test_plan_02_24_amm_monitor_mempool_watcher_unit.py`.

---

## Testing approach

AMMMonitor has no pure static functions — all are instance methods accessing `_state`, `_lock`, and `_last_quoted_buy/sell`. Tests instantiate the class without calling `start()` (no background thread) and inject state directly via `mon._state = {...}` and `mon._last_quoted_buy = ...`. Config is patched by replacing `config.cfg` in the `config` module (since methods do `from config import cfg` lazily at call time).

---

## No bugs found
