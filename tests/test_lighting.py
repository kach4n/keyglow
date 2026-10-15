import json
import tempfile
import unittest
from pathlib import Path

from keyglow import layout, lighting, patterns
from keyglow.profiles import Store, default_profile


class LayoutTests(unittest.TestCase):
    def test_104_keys_with_unique_leds(self):
        leds = [k["led"] for k in layout.KEYS]
        self.assertEqual(len(leds), 104)
        self.assertEqual(len(set(leds)), 104)
        self.assertTrue(all(0 <= i < layout.LED_COUNT for i in leds))

    def test_leds_confirmed_on_hardware(self):
        by_label = {k["label"]: k["led"] for k in layout.KEYS}
        self.assertEqual(by_label["Esc"], 1)
        self.assertEqual(by_label["Q"], 38)
        self.assertEqual(by_label["A"], 56)
        self.assertEqual(by_label[""], 94)        # space bar
        self.assertEqual(layout.led_index(5, 16), 106)  # numpad Enter
        self.assertEqual(layout.led_index(4, 14), 140)  # numpad 1


class LightingBlockTests(unittest.TestCase):
    def test_block_shape(self):
        block = lighting.build(default_profile(1))
        self.assertEqual(len(block), 15 * 64)
        self.assertEqual([block[i * 64] for i in range(5)], [1, 3, 4, 5, 8])
        self.assertEqual(block[-2:], b"\xaa\x55")

    def test_custom_matches_hardware_verified_bytes(self):
        """Per-key part of the block that lit Esc/Q/A/Space/NumEnter on the real keyboard."""
        p = default_profile(1)
        p["mode"] = "custom"
        p["effects"]["custom"] = {"brightness": 5, "keys": {
            "1": "#ffffff", "38": "#00ff00", "56": "#0000ff", "94": "#ff0000", "106": "#ffff00"}}
        block = lighting.build(p)
        expected = bytearray(0x240)
        for i in range(144):
            expected[i * 4] = 0x80
        for led, rgb in {1: (255, 255, 255), 38: (0, 255, 0), 56: (0, 0, 255), 94: (255, 0, 0), 106: (255, 255, 0)}.items():
            expected[led * 4 + 1:led * 4 + 4] = bytes(rgb)
        self.assertEqual(block[5 * 64:5 * 64 + 0x240], bytes(expected))
        tail = block[-64:]
        self.assertEqual((tail[0], tail[1]), (0x80, 5))

    def test_static_slot(self):
        p = default_profile(1)
        p["mode"] = "static"
        p["effects"]["static"] = {"color": "#ff0000", "brightness": 5}
        block = lighting.build(p)
        slot = block[2 * 64:3 * 64]
        self.assertEqual(bytes(slot[:4]), b"\x04\xff\x00\x00")
        self.assertEqual(slot[0x3E], 5)
        self.assertEqual(block[-64], 0x04)

    def test_values_are_clamped(self):
        p = default_profile(1)
        p["effects"]["wave"].update(speed=99, brightness=-3, direction=7)
        slot = lighting.build(p)[3 * 64:4 * 64]
        self.assertEqual((slot[0x3D], slot[0x3E], slot[0x3F]), (3, 0, 5))


class PatternTests(unittest.TestCase):
    def test_every_pattern_colors_every_key(self):
        leds = {str(k["led"]) for k in layout.KEYS}
        for name, keys in patterns.all_patterns().items():
            self.assertEqual(set(keys), leds, name)
            self.assertTrue(all(len(c) == 7 and c[0] == "#" for c in keys.values()), name)


class StoreTests(unittest.TestCase):
    def test_round_trip_and_defaults_for_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"active": 3, "profiles": [{"name": "Old", "mode": "static"}]}))
            store = Store(path)
            self.assertEqual(store.data["active"], 3)
            self.assertEqual(store.data["profiles"][0]["name"], "Old")
            self.assertIn("wave", store.data["profiles"][0]["effects"])
            store.save()
            self.assertEqual(Store(path).data, store.data)


if __name__ == "__main__":
    unittest.main()
