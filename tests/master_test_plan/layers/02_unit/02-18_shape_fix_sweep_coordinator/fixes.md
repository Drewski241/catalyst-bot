# Fixes — Slice 02-18

No production code fixes needed. All 40 tests passed on first run.

## Side-effect fix applied (02-24 isolation)

While running the full suite discovered that `test_dynamic_amm_buffer.py` tearDown removes
`"config"` from `sys.modules`, breaking lazy `from config import cfg` in `amm_monitor.py`.
Fixed `TestCheckAmmBuffer` setUp/tearDown/_set_cfg in `test_plan_02_24_...` to re-register
`_config_module` into `sys.modules["config"]` so patched cfg is always visible to callers.
