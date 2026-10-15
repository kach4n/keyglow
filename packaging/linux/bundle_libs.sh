#!/bin/sh
# Copies shared libraries that the bundled Qt needs but PyInstaller left out
# (mostly X11/xcb/Wayland client libraries loaded by Qt's platform plugins)
# from the build machine into the app folder.
# GPU driver libraries (GL/EGL/GBM/DRM, Mesa) stay with the system: they are
# hardware-specific and every desktop has them.
set -e
app="$1/_internal"
export LD_LIBRARY_PATH="$app:$app/PyQt6/Qt6/lib"

missing() {
    find "$app" -name '*.so*' -type f -exec ldd {} + 2>/dev/null \
        | awk '/not found/ {print $1}' | sort -u \
        | grep -Ev '^lib(GL|GLX|GLdispatch|EGL|OpenGL|gbm|drm|nvidia|mesa)' || true
}

for round in 1 2 3; do           # copied libraries can need more libraries
    libs=$(missing)
    [ -z "$libs" ] && break
    for lib in $libs; do
        src=$(ldconfig -p | awk -v l="$lib" '$1 == l && /x86-64/ {print $NF; exit}')
        if [ -n "$src" ]; then
            cp -L "$src" "$app/$lib"
            echo "bundled $lib"
        else
            echo "warning: $lib not available on the build machine"
        fi
    done
done

left=$(missing)
[ -z "$left" ] || { echo "Still missing:"; echo "$left"; }
