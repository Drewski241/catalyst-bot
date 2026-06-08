# v1.2.46.3 — Disable Linux system tray with Qt desktop

Fixes desktop crashes on Ubuntu where the app reached
`Desktop window URL: http://127.0.0.1:5000/` then aborted with:

- `QObject::killTimer: Timers cannot be stopped from another thread`
- `g_main_context_push_thread_default: assertion 'acquired_context' failed`

Root cause: **pystray** (GTK/AppIndicator) running beside the bundled **PyQt6**
WebEngine event loop.

## Fix

- Disable the system tray by default on Linux when the Qt desktop backend is used
- Tray can still be forced with `CATALYST_ENABLE_TRAY=1` (may crash on some setups)
- Keeps v1.2.46.2 loopback + software-rendering fixes

## Install

```bash
sudo apt install ./catalyst_v1.2.46.3_amd64.deb
catalyst
```
