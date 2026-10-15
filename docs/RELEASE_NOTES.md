KeyGlow is a lighting app for the HyperX Mars Gaming Keyboard (USB `0951:16C6`). Both downloads are fully portable: Python, the UI and everything else is bundled.

### Windows 10/11
Download **`KeyGlow.exe`** and run it. There's nothing to install. It uses the WebView2 runtime, which comes with Windows 11 and current Windows 10. The exe isn't code-signed, so SmartScreen may warn the first time: choose *More info → Run anyway*.

### Linux (x86_64, Ubuntu 22.04 or newer and similar distros)
```sh
tar -xzf KeyGlow-linux-x86_64.tar.gz
cd KeyGlow
./install.sh      # one time: lets your user reach the keyboard, adds a menu entry
./KeyGlow
```
Gaming mode is Windows-only. Everything else works the same on both systems.

### What's new in 1.1.0
- **Linux version.**
- **Brasil pattern:** now uses pure green, yellow and blue, so it looks right on the LEDs.
- **Tested builds:** releases are now built and smoke-tested by GitHub Actions, and the Linux build is checked on a clean Ubuntu with no Python installed.
