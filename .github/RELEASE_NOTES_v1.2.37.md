## CATalyst v1.2.37

Official release line. Use this tag — not the mistaken `v1.2.6` publish on some forks.

### Linux (Ubuntu 24.04 Noble)

- `.deb` and AppImage with bundled Qt/PyQt6 desktop backend
- Declared WebKit, XCB, and notification dependencies in the Debian package

```bash
sudo apt install ./catalyst_v1.2.37_amd64.deb
catalyst
```

Optional system tray support:

```bash
sudo apt install gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1
```

Download: https://github.com/catalystxch/catalyst-bot/releases/tag/v1.2.37
