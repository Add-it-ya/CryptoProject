"""Creates the test image used in the ECB pattern-leak experiment: flat colour regions (like a logo,
scanned form or chart), which is exactly the kind of content where ECB mode leaks structure."""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 512, 384
img = Image.new("RGB", (W, H), (236, 240, 245))
d = ImageDraw.Draw(img)
# cloud
for (cx, cy, r) in [(170, 170, 70), (250, 130, 90), (340, 170, 70)]:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 64, 175))
d.rectangle([100, 170, 410, 240], fill=(30, 64, 175))
# padlock
d.rounded_rectangle([205, 150, 305, 230], radius=10, fill=(250, 204, 21))
d.arc([220, 95, 290, 175], start=180, end=360, fill=(250, 204, 21), width=14)
d.ellipse([244, 172, 266, 194], fill=(30, 41, 59))
d.rectangle([251, 185, 259, 212], fill=(30, 41, 59))
# text
try:
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 46)
except Exception:
    f = ImageFont.load_default()
d.text((W // 2, 310), "GROUP 18", fill=(15, 23, 42), font=f, anchor="mm")
out = sys.argv[1]
img.save(out, format="BMP")
print("wrote", out, img.size)
