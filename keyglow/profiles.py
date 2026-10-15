"""Profiles stored as JSON: %APPDATA%\\KeyGlow\\settings.json on Windows,
~/.config/KeyGlow/settings.json on Linux."""

import copy
import json
import os
from pathlib import Path

PROFILE_COUNT = 10
_PALETTE = ["#ff0000", "#ff00ff", "#00ff00", "#ffff00", "#0000ff"]


def default_profile(number):
    return {
        "name": f"Profile {number}",
        "mode": "wave",
        "effects": {
            "static": {"color": "#ff0000", "brightness": 5},
            "breathing": {"colors": list(_PALETTE), "speed": 3, "brightness": 5, "loop": False},
            "spectrum": {"speed": 3, "brightness": 5},
            "wave": {"direction": 0, "speed": 3, "brightness": 5},
            "stack": {"direction": 1, "colors": list(_PALETTE), "speed": 3, "brightness": 5, "loop": True},
            "custom": {"brightness": 5, "keys": {}},
        },
        "gaming": {"win": False, "alt_tab": False, "alt_f4": False},
    }


def default_settings():
    return {"active": 0, "profiles": [default_profile(i + 1) for i in range(PROFILE_COUNT)],
            "designs": {}}


def _merge(base, saved):
    """Fill keys missing from older settings files with defaults."""
    out = copy.deepcopy(base)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict) and key != "keys":
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Store:
    def __init__(self, path=None):
        if os.name == "nt":
            root = Path(os.environ.get("APPDATA", Path.home())) / "KeyGlow"
        else:
            root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "KeyGlow"
        self.path = Path(path) if path else root / "settings.json"
        self.data = self._load()

    def _load(self):
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default_settings()
        data = default_settings()
        data["active"] = int(saved.get("active", 0)) % PROFILE_COUNT
        data["designs"] = saved.get("designs", {})
        for i, profile in enumerate(saved.get("profiles", [])[:PROFILE_COUNT]):
            data["profiles"][i] = _merge(default_profile(i + 1), profile)
        return data

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        tmp.replace(self.path)
