#!/bin/sh
# Copies every shared library the app takes from the build machine into the
# app folder, so it runs on systems that lack them (X11/xcb/Wayland client
# libraries for Qt's platform plugins are the usual gap).
# Kept with the system: the C runtime (must match the user's kernel/glibc),
# GPU driver libraries (GL/EGL/GBM/DRM, hardware-specific, every desktop has
# them) and PulseAudio (only Qt's audio plugins use it; KeyGlow loads none).
set -e
app="$(cd "$1" && pwd)/_internal"
export LD_LIBRARY_PATH="$app:$app/PyQt6/Qt6/lib"
skip='^(ld-linux.*|lib(c|m|dl|pthread|rt|resolv|util|gcc_s|stdc\+\+)\.so.*|lib(GL|GLX|GLdispatch|EGL|OpenGL|gbm|drm|vulkan|pulse).*)$'

deps() {
    find "$app" -name '*.so*' -type f -exec ldd {} + 2>/dev/null \
        | awk -v app="$app" '$2 == "=>" && $3 ~ /^\// && index($3, app) != 1 {print $1, $3}' \
        | sort -u
}

for round in 1 2 3 4; do         # bundled libraries can pull in more libraries
    added=0
    deps | while read -r name path; do
        echo "$name" | grep -Eq "$skip" && continue
        [ -e "$app/$name" ] && continue
        cp -L "$path" "$app/$name"
        echo "bundled $name"
    done > /tmp/keyglow-bundled.txt
    cat /tmp/keyglow-bundled.txt
    [ -s /tmp/keyglow-bundled.txt ] || break
done

echo "Left to the system:"
deps | awk '{print "  " $1}'
