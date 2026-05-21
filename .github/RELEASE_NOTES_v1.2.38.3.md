# v1.2.38.3 — Linux desktop + coin prep fix

## Includes

- **Desktop window (Linux):** loads `http://127.0.0.1:5000/` directly; Qt loopback flags in `.deb`/AppImage launchers
- **Coin prep (Linux `.deb`):** logs and status under `~/.local/share/Catalyst/` (fixes Permission denied on `/opt/catalyst/_internal/`)
- **CI:** Windows release no longer fails when update-signing secret is missing; Linux `.deb` still publishes

## Install (Ubuntu)

```bash
sudo apt install ./catalyst_v1.2.38.3_amd64.deb
```

## Verify

```bash
dpkg -l catalyst
test -f /opt/catalyst/linux-desktop-loopback-fix.txt && cat /opt/catalyst/linux-desktop-loopback-fix.txt
catalyst 2>&1 | grep "Desktop window URL"
```

Expected: version **1.2.38.3**, stamp file present, `Desktop window URL: http://127.0.0.1:5000/`
