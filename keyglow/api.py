"""Functions the web UI calls through pywebview's js_api."""

import sys
import threading

from . import layout, lighting, patterns
from .device import DeviceError, Keyboard
from .profiles import Store

if sys.platform == "win32":
    from .gamingmode import GamingMode
else:
    GamingMode = None       # needs a global keyboard hook; Windows only for now


class Api:
    def __init__(self, store=None):
        self._store = store or Store()
        self._kb = None
        self._kb_lock = threading.Lock()
        self._gaming = GamingMode() if GamingMode else None
        self._apply_gaming()

    # -- device ------------------------------------------------------------
    def _keyboard(self):
        if self._kb is None:
            self._kb = Keyboard.find()
        return self._kb

    def _drop(self):
        if self._kb:
            self._kb.close()
        self._kb = None

    def _write(self, block):
        with self._kb_lock:
            for attempt in range(2):
                try:
                    kb = self._keyboard()
                    if kb is None:
                        return {"ok": False, "message": "Keyboard not found. Check that it is plugged in."}
                    kb.write_block(0x0A, block)
                    return {"ok": True, "message": "Saved to the keyboard."}
                except (DeviceError, OSError) as e:
                    self._drop()
                    if attempt:
                        return {"ok": False, "message": str(e)}

    def device_status(self):
        with self._kb_lock:
            try:
                kb = self._keyboard()
                if kb is None:
                    return {"connected": False, "message": "Keyboard not found"}
                kb.is_ready()
            except (DeviceError, OSError) as e:
                self._drop()
                return {"connected": False, "message": str(e)}
            v = kb.version
            return {"connected": True, "firmware": f"{v >> 8}.{v & 0xFF:02d}"}

    # -- UI calls ----------------------------------------------------------
    def get_init(self):
        return {
            "layout": {"keys": layout.KEYS, "width": layout.WIDTH, "height": layout.HEIGHT},
            "settings": self._store.data,
            "patterns": patterns.all_patterns(),
            "limits": {"brightness": lighting.MAX_BRIGHTNESS, "speed": list(lighting.SPEEDS)},
            "features": {"gaming_mode": self._gaming is not None},
        }

    def save_settings(self, settings):
        self._store.data = settings
        self._store.save()
        self._apply_gaming()
        return True

    def apply(self, settings):
        """Save settings and write the active profile's lighting to the keyboard."""
        self.save_settings(settings)
        profile = settings["profiles"][settings["active"]]
        return self._write(lighting.build(profile))

    def lights_off(self):
        profile = self._store.data["profiles"][self._store.data["active"]]
        return self._write(lighting.off_block(profile))

    def _apply_gaming(self):
        if not self._gaming:
            return
        data = self._store.data
        g = data["profiles"][data["active"]]["gaming"]
        self._gaming.configure(g.get("win"), g.get("alt_tab"), g.get("alt_f4"))

    def shutdown(self):
        if self._gaming:
            self._gaming.stop()
        self._drop()
