#!/bin/sh
# Copies the shared libraries the app takes from the build machine into the
# app folder, so it runs on systems that lack them (the xcb helper libraries
# and xkbcommon-x11 used by Qt's X11 plugin are the usual gap).
#
# Like AppImage's excludelist, it never bundles libraries that every Linux
# desktop has and that the GPU driver loads into the same process: the C
# runtime, GL/EGL/GBM/DRM, core X11/xcb, Wayland, expat, zlib, glib, dbus,
# fontconfig/freetype. Bundling older copies of those breaks the system's
# graphics driver. PulseAudio is only used by Qt audio plugins KeyGlow never loads.
set -e
app="$(cd "$1" && pwd)/_internal"
export LD_LIBRARY_PATH="$app:$app/PyQt6/Qt6/lib"
skip='^(ld-linux.*|lib(c|m|dl|pthread|rt|resolv|util|gcc_s|stdc\+\+|z|expat|uuid)\.so.*'
skip="$skip"'|lib(GL|GLX|GLdispatch|EGL|OpenGL|gbm|drm|vulkan|LLVM|elf|sensors|pciaccess|pulse|wayland-).*'
skip="$skip"'|lib(X11|X11-xcb|Xext|Xfixes|Xxf86vm|Xau|Xdmcp|xshmfence|ICE|SM)\.so.*'
skip="$skip"'|libxcb\.so.*|libxcb-(dri2|dri3|glx|present|sync|xfixes|randr|shm)\.so.*'
skip="$skip"'|lib(glib|gobject|gio|gmodule|gthread)-2\.0\.so.*|lib(dbus-1|fontconfig|freetype|systemd|udev|ffi|pcre2?-8|selinux|mount|blkid)\.so.*)$'

# PyInstaller bundles some of these by itself; drop them so the system copies load.
for path in "$app"/*.so*; do
    name=$(basename "$path")
    if echo "$name" | grep -Eq "$skip"; then
        rm -f "$path"
        echo "unbundled $name"
    fi
done

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
