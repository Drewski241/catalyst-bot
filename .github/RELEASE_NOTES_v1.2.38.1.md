## CATalyst v1.2.38.1 (test) — Linux native window fix

**Replaces v1.2.38 test deb** which was built without the loopback URL fix wired into the PyInstaller bundle.

### Fix
- Native Linux window loads `http://127.0.0.1:5000/` directly (no `file://` splash redirect)
- Fixes `ERR_NETWORK_ACCESS_DENIED` / "Your Internet access is blocked" in the Qt WebEngine shell
- `catalyst` launcher and AppImage export Qt WebEngine loopback flags
- Build stamp: `linux-desktop-loopback-fix.txt` inside the package

### Install

```bash
sudo apt install ./catalyst_v1.2.38.1_amd64.deb
catalyst
```

When starting from a terminal you should see:
`Desktop window URL: http://127.0.0.1:5000/`
