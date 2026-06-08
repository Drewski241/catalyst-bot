# v1.2.46.1 — Linux desktop loopback fix (Drewski241 release)

Based on upstream **v1.2.46** with the Linux `ERR_NETWORK_ACCESS_DENIED` fix restored.

## Includes

- **All v1.2.46 features** from catalystxch (Sage mempool fixes, PC diagnostics, packaging hardening, etc.)
- **Linux desktop window:** loads `http://127.0.0.1:5000/` directly on Linux (skips `file://` splash redirect)
- **Qt WebEngine:** `QTWEBENGINE_CHROMIUM_FLAGS` set in app and `.deb`/AppImage launchers
- **WebKit fallback:** `WEBKIT_DISABLE_SANDBOX=1` kept for GTK backend paths
- **Build guard:** `build.py` verifies loopback fix before PyInstaller runs

## Install (Ubuntu)

```bash
sudo apt install ./catalyst_v1.2.46.1_amd64.deb
catalyst
```

## Verify

```bash
dpkg -l catalyst
test -f /opt/catalyst/linux-desktop-loopback-fix.txt && cat /opt/catalyst/linux-desktop-loopback-fix.txt
catalyst 2>&1 | grep "Desktop window URL"
```

Expected: version **1.2.46.1**, stamp file present, `Desktop window URL: http://127.0.0.1:5000/`
