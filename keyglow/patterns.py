"""Per-key color designs. Each pattern maps LED index -> '#rrggbb'.

These are stored on the keyboard as a custom layout, so they cost one
write when applied and nothing afterwards.
"""

import colorsys
import math
import random

from .layout import HEIGHT, KEYS, WIDTH


def _hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in (r, g, b))


def _hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return _hex(r * 255, g * 255, b * 255)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _gradient(stops, t):
    """stops: list of (position 0..1, (r, g, b))."""
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            return _hex(*_mix(c0, c1, (t - p0) / (p1 - p0 or 1)))
    return _hex(*stops[-1][1])


def _centers():
    for k in KEYS:
        yield k, (k["x"] + k["w"] / 2) / WIDTH, (k["y"] + k["h"] / 2) / HEIGHT


def _by_position(fn):
    return {str(k["led"]): fn(k, x, y) for k, x, y in _centers()}


def rainbow():
    return _by_position(lambda k, x, y: _hsv(x * 0.85))


def rainbow_diagonal():
    return _by_position(lambda k, x, y: _hsv((x * 0.75 + y * 0.35) * 0.9))


def rainbow_rows():
    return _by_position(lambda k, x, y: _hsv(round(y * 5) / 6.0))


def sunset():
    stops = [(0, (255, 214, 64)), (0.45, (255, 94, 58)), (0.75, (200, 30, 120)), (1, (70, 20, 150))]
    return _by_position(lambda k, x, y: _gradient(stops, 1 - y + 0.15 * math.sin(x * 6)))


def ocean():
    stops = [(0, (230, 255, 255)), (0.35, (0, 210, 220)), (0.7, (0, 90, 220)), (1, (10, 20, 120))]
    return _by_position(lambda k, x, y: _gradient(stops, y + 0.12 * math.sin(x * 9)))


def aurora():
    stops = [(0, (0, 255, 120)), (0.5, (0, 200, 255)), (1, (160, 40, 255))]
    return _by_position(lambda k, x, y: _gradient(stops, 0.5 + 0.5 * math.sin(x * 7 + y * 3)))


def fire():
    rng = random.Random(7)
    stops = [(0, (255, 240, 120)), (0.35, (255, 140, 0)), (0.7, (230, 30, 0)), (1, (120, 0, 0))]
    return _by_position(lambda k, x, y: _gradient(stops, (1 - y) * 0.9 + rng.uniform(-0.15, 0.15)))


def lava():
    stops = [(0, (40, 0, 0)), (0.5, (220, 30, 0)), (1, (255, 180, 0))]
    return _by_position(lambda k, x, y: _gradient(stops, 0.5 + 0.5 * math.sin(x * 11) * math.cos(y * 7)))


def synthwave():
    def color(k, x, y):
        row = round(y * 5)
        if row in (1, 4):
            return "#00e5ff"
        return _gradient([(0, (255, 0, 170)), (1, (90, 0, 200))], x)
    return _by_position(color)


def cyberpunk():
    def color(k, x, y):
        if k["label"] in ("Esc", "Enter", "Backspace", "", "Shift"):
            return "#ff00a0"
        return "#fcee0a" if x < 0.62 else "#00f0ff"
    return _by_position(color)


def matrix():
    rng = random.Random(42)
    return _by_position(lambda k, x, y: _hex(0, rng.choice((40, 90, 160, 255)), rng.choice((0, 0, 30))))


def galaxy():
    rng = random.Random(11)

    def color(k, x, y):
        if rng.random() < 0.12:
            return "#ffffff"
        return _gradient([(0, (20, 0, 60)), (1, (120, 0, 160))], 0.5 + 0.5 * math.sin(x * 5 + y * 4))
    return _by_position(color)


def ice():
    return _by_position(lambda k, x, y: _gradient([(0, (255, 255, 255)), (1, (60, 170, 255))], y * 0.8 + x * 0.2))


def forest():
    stops = [(0, (180, 255, 60)), (0.5, (0, 170, 40)), (0.85, (0, 80, 20)), (1, (110, 60, 10))]
    return _by_position(lambda k, x, y: _gradient(stops, y))


def candy():
    rng = random.Random(3)
    palette = ["#ff8fd8", "#8fe3ff", "#fff38f", "#b98fff", "#8fffb3", "#ffb38f"]
    return _by_position(lambda k, x, y: rng.choice(palette))


def water_ripple():
    """Concentric rings around the middle of the board, like a drop hitting water."""
    cx, cy = 7.0 / WIDTH, 3.75 / HEIGHT

    def color(k, x, y):
        d = math.hypot((x - cx) * WIDTH / HEIGHT, y - cy)
        ring = 0.5 + 0.5 * math.cos(d * 22)
        return _hex(*_mix((0, 40, 160), (190, 250, 255), ring * max(0.25, 1 - d * 0.5)))
    return _by_position(color)


def gamer_wasd():
    hot = {"W", "A", "S", "D", "Q", "E", "R", "F", "", "Shift", "Ctrl", "Esc",
           "1", "2", "3", "4", "↑", "←", "↓", "→"}

    def color(k, x, y):
        if k["label"] in ("W", "A", "S", "D", "↑", "←", "↓", "→"):
            return "#00ffff"
        if k["label"] in hot and x < 0.7:
            return "#ff2a2a"
        return "#2a0000"
    return _by_position(color)


def typing_zones():
    """Touch-typing finger zones, one color per finger."""
    zones = {"pinkyL": "#ff3b6b", "ringL": "#ff9f1c", "middleL": "#ffe14d", "indexL": "#3cff7a",
             "indexR": "#29d0ff", "middleR": "#5b6cff", "ringR": "#b04dff", "pinkyR": "#ff4df0", "thumb": "#ffffff"}
    columns = [
        ("pinkyL", "`1QAZ"), ("ringL", "2WSX"), ("middleL", "3EDC"), ("indexL", "45RTFGVB"),
        ("indexR", "67YUHJNM"), ("middleR", "8IK,"), ("ringR", "9OL."), ("pinkyR", "0P;/-=[]'\\"),
    ]
    lookup = {ch: zones[z] for z, chars in columns for ch in chars}

    def color(k, x, y):
        if k["label"] == "":
            return zones["thumb"]
        if k["x"] < 15 and k["label"] in lookup:
            return lookup[k["label"]]
        return "#202020"
    return _by_position(color)


def brasil():
    def color(k, x, y):
        dx, dy = (x - 0.33) * 2.2, (y - 0.5) * 2
        # Pure primaries: LEDs turn mixed tones like #00a83c into teal/blue.
        if math.hypot(dx * 1.6, dy) < 0.45:
            return "#0000ff"
        if abs(dx) + abs(dy) < 1.0:
            return "#ffff00"
        return "#00ff00"
    return _by_position(color)


def police():
    return _by_position(lambda k, x, y: "#ff0000" if x < 0.5 else "#0040ff")


def pure_white():
    return _by_position(lambda k, x, y: "#ffffff")


PATTERNS = {
    "Rainbow": rainbow,
    "Rainbow diagonal": rainbow_diagonal,
    "Rainbow rows": rainbow_rows,
    "Water ripple": water_ripple,
    "Sunset": sunset,
    "Ocean": ocean,
    "Aurora": aurora,
    "Synthwave": synthwave,
    "Cyberpunk": cyberpunk,
    "Galaxy": galaxy,
    "Fire": fire,
    "Lava": lava,
    "Matrix": matrix,
    "Ice": ice,
    "Forest": forest,
    "Candy": candy,
    "Gamer WASD": gamer_wasd,
    "Typing zones": typing_zones,
    "Brasil": brasil,
    "Police": police,
    "Pure white": pure_white,
}


def all_patterns():
    return {name: fn() for name, fn in PATTERNS.items()}
