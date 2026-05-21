## CATalyst v1.2.6 — Ubuntu 24.04 stable release

### Linux (Ubuntu 24.04 Noble)

- Bundle the Qt/PyQt6 desktop backend inside AppImage and `.deb` packages so PyWebView no longer depends on fragile system Python symlinks under `/opt/catalyst`.
- Declare Ubuntu 24.04 runtime libraries in the `.deb` control file, including `libwebkit2gtk-4.1-0`, `libnotify-bin`, and the XCB packages required by the Qt window.
- Run desktop smoke tests in CI (xvfb) for both AppImage and `.deb` payloads before publishing release assets.

### Install on Ubuntu 24.04

```bash
sudo apt install ./catalyst_v1.2.6_amd64.deb
catalyst
```

Portable alternative:

```bash
chmod +x Catalyst-linux-v1.2.6-x86_64.AppImage
./Catalyst-linux-v1.2.6-x86_64.AppImage
```

### Also in this release

- Spacescan API key validation diagnostics in the GUI.
- Linux notification identity hardening for desktop alerts.
- Non-Windows guardrails in the in-app updater flow.
