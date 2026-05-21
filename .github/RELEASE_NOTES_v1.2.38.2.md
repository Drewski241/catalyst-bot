# v1.2.38.2 — Linux desktop window (test build)

## What was wrong

v1.2.38 and v1.2.38.1 `.deb` packages could still ship a binary built **without** the loopback fix. Startup logs from those builds never show:

`Desktop window URL: http://127.0.0.1:5000/`

That line is required on fixed builds. Without it, the window loads `file://` splash and Qt WebEngine blocks the redirect to Flask (`ERR_NETWORK_ACCESS_DENIED`).

## What changed

- **Build gate:** `python build.py` now runs `_verify_linux_desktop_source()` before PyInstaller so a bad `desktop_app.py` cannot be packaged.
- **Frozen Linux:** force PyWebView `gui=qt` when `sys.frozen` (PyInstaller) even if `find_spec("qtpy")` fails.
- **Packaging:** `.deb` / AppImage launchers set `FONTCONFIG_FILE` when system fonts exist (fixes blank UI / Fontconfig errors).
- **CI smoke:** `linux_desktop_smoke.sh` fails if the loopback URL line is missing from the log.

## Verify after install

```bash
dpkg -l catalyst
test -f /opt/catalyst/linux-desktop-loopback-fix.txt && cat /opt/catalyst/linux-desktop-loopback-fix.txt
catalyst 2>&1 | tee /tmp/catalyst-start.log
grep "Desktop window URL" /tmp/catalyst-start.log
```

You should see:

`Desktop window URL: http://127.0.0.1:5000/`

## Workaround (unchanged)

```bash
catalyst --flask
# open http://127.0.0.1:5000/ in Firefox
```
