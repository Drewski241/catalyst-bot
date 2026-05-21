## CATalyst v1.2.38 (test build)

**Linux desktop fix:** native window loads `http://127.0.0.1:5000/` directly instead of `file://` splash redirect, fixing `ERR_NETWORK_ACCESS_DENIED` in Qt WebEngine.

### Install (Ubuntu 24.04)

```bash
sudo apt install ./catalyst_v1.2.38_amd64.deb
catalyst
```

### Also includes

- Qt/PyQt6 bundled desktop backend
- AppIndicator + fontconfig in `.deb` dependencies (system tray)
- Qt WebEngine loopback flags in `catalyst` launcher and AppImage `AppRun`
