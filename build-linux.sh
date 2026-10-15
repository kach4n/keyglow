#!/bin/sh
# Builds dist/KeyGlow-linux-x86_64.tar.gz: a self-contained folder with the
# KeyGlow binary (Python, Qt and the web engine bundled), the udev rule and
# an install script. Build on the oldest distro you want to support.
set -e
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements-linux.txt pyinstaller pillow
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/make_icon.py --png

.venv/bin/pyinstaller --noconfirm --clean --onedir --windowed \
    --name KeyGlow \
    --add-data "keyglow/web:keyglow/web" \
    --collect-all webview \
    --workpath build/linux --distpath dist/linux \
    keyglow_app.py

cp packaging/linux/99-keyglow.rules packaging/linux/install.sh assets/keyglow.png dist/linux/KeyGlow/
chmod +x dist/linux/KeyGlow/install.sh
tar -C dist/linux -czf dist/KeyGlow-linux-x86_64.tar.gz KeyGlow
echo "Built dist/KeyGlow-linux-x86_64.tar.gz"
