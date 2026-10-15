"""Draws assets/keyglow.ico (or assets/keyglow.png with --png): a glowing keyboard."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(base)
d.rounded_rectangle((8, 8, S - 8, S - 8), 56, fill=(16, 18, 26, 255))
colors = [(255, 61, 119), (255, 160, 60), (122, 92, 255), (34, 211, 238), (52, 211, 153)]
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
g = ImageDraw.Draw(glow)
for row in range(3):
    for col in range(5):
        x, y = 40 + col * 36, 70 + row * 40
        g.rounded_rectangle((x, y, x + 28, y + 30), 7, fill=colors[(col + row) % 5] + (255,))
g.rounded_rectangle((76, 190, 180, 214), 8, fill=(122, 92, 255, 255))
img = Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(10)))
img = Image.alpha_composite(img, glow)
assets = Path(__file__).resolve().parent.parent / "assets"
if "--png" in sys.argv:            # Linux desktop icon
    out = assets / "keyglow.png"
    img.save(out)
else:
    out = assets / "keyglow.ico"
    img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", out)
