#!/bin/sh
# Installs the udev rule so KeyGlow can reach the keyboard without root,
# and adds KeyGlow to the application menu. Run from the extracted folder:
#   ./install.sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"

echo "Installing udev rule (asks for your password)..."
sudo install -m 0644 "$here/99-keyglow.rules" /etc/udev/rules.d/99-keyglow.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps"
cat > "$apps/keyglow.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=KeyGlow
Comment=Keyboard lighting for the HyperX Mars Gaming Keyboard
Exec="$here/KeyGlow"
Icon=$here/keyglow.png
Terminal=false
Categories=Utility;Settings;
EOF

echo "Done. If KeyGlow says it has no permission, unplug and replug the keyboard."
echo "Start it from your app menu or with: $here/KeyGlow"
