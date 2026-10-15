"""Builds the lighting block that the keyboard stores (command 04 0A).

Block layout (15 x 64 bytes = 960 bytes):
  5 effect slots, 64 bytes each, starting with the effect's mode byte
  144 LED entries of 4 bytes: 0x80, R, G, B   (custom per-key colors)
  64-byte tail: [0] active mode, [1] custom brightness, [62..63] AA 55
The keyboard only accepts exactly five effect slots.
"""

from .layout import LED_COUNT

MODES = {
    "breathing": 0x01,
    "spectrum": 0x03,
    "static": 0x04,
    "wave": 0x05,
    "stack": 0x08,
    "custom": 0x80,
}

MAX_BRIGHTNESS = 5
SPEEDS = (1, 5)
DIRECTIONS = 4


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _clamp(value, low, high):
    return max(low, min(high, int(value)))


def _colors(slot, colors):
    for i, color in enumerate((list(colors) + ["#000000"] * 5)[:5]):
        slot[1 + i * 3:4 + i * 3] = bytes(hex_to_rgb(color))


def _breathing(s):
    slot = bytearray(64)
    slot[0] = MODES["breathing"]
    _colors(slot, s["colors"])
    slot[0x3C] = 1 if s.get("loop") else 0
    slot[0x3E] = _clamp(s["brightness"], 0, MAX_BRIGHTNESS)
    slot[0x3F] = _clamp(s["speed"], *SPEEDS)
    return slot


def _spectrum(s):
    slot = bytearray(64)
    slot[0] = MODES["spectrum"]
    slot[0x3E] = _clamp(s["brightness"], 0, MAX_BRIGHTNESS)
    slot[0x3F] = _clamp(s["speed"], *SPEEDS)
    return slot


def _static(s):
    slot = bytearray(64)
    slot[0] = MODES["static"]
    slot[1:4] = bytes(hex_to_rgb(s["color"]))
    slot[0x3E] = _clamp(s["brightness"], 0, MAX_BRIGHTNESS)
    return slot


def _wave(s):
    slot = bytearray(64)
    slot[0] = MODES["wave"]
    slot[0x3D] = _clamp(s["direction"], 0, DIRECTIONS - 1)
    slot[0x3E] = _clamp(s["brightness"], 0, MAX_BRIGHTNESS)
    slot[0x3F] = _clamp(s["speed"], *SPEEDS)
    return slot


def _stack(s):
    slot = bytearray(64)
    slot[0] = MODES["stack"]
    _colors(slot, s["colors"])
    slot[0x3C] = 1 if s.get("loop") else 0
    slot[0x3D] = _clamp(s["direction"], 0, DIRECTIONS - 1)
    slot[0x3E] = _clamp(s["brightness"], 0, MAX_BRIGHTNESS)
    slot[0x3F] = _clamp(s["speed"], *SPEEDS)
    return slot


def build(profile):
    """Return the 960-byte lighting block for a profile dict (see profiles.default_profile)."""
    fx = profile["effects"]
    slots = _breathing(fx["breathing"]) + _spectrum(fx["spectrum"]) + _static(fx["static"]) \
        + _wave(fx["wave"]) + _stack(fx["stack"])

    leds = bytearray(LED_COUNT * 4)
    custom = fx["custom"]
    for i in range(LED_COUNT):
        leds[i * 4] = 0x80
    for led, color in custom["keys"].items():
        led = int(led)
        if 0 <= led < LED_COUNT:
            leds[led * 4 + 1:led * 4 + 4] = bytes(hex_to_rgb(color))

    tail = bytearray(64)
    tail[0] = MODES[profile["mode"]]
    tail[1] = _clamp(custom["brightness"], 0, MAX_BRIGHTNESS)
    tail[0x3E:0x40] = b"\xaa\x55"
    return bytes(slots + leds + tail)


def off_block(profile):
    """A block that turns every LED off (custom mode, all keys black)."""
    dark = {**profile, "mode": "custom",
            "effects": {**profile["effects"], "custom": {"brightness": 0, "keys": {}}}}
    return build(dark)
