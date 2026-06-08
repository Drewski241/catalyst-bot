# v1.2.46.2 — Linux Qt software rendering fix

Fixes desktop crashes on some NVIDIA/hybrid GPU Ubuntu setups after v1.2.46.1
opened the loopback URL correctly but aborted with GBM/Vulkan/OpenGL errors.

## Includes

- **v1.2.46.1 loopback fix** (unchanged)
- **Software Qt rendering** in app startup and `.deb`/AppImage launchers:
  - `QT_OPENGL=software`, `LIBGL_ALWAYS_SOFTWARE=1`
  - Chromium flags: `--disable-gpu --no-sandbox --disable-dev-shm-usage`
- **Tray workaround:** set `CATALYST_DISABLE_TRAY=1` if a desktop still crashes

## Install (Ubuntu)

```bash
sudo apt install ./catalyst_v1.2.46.2_amd64.deb
catalyst
```

## If it still crashes

```bash
CATALYST_DISABLE_TRAY=1 catalyst
```
