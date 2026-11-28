# generates the wheel-track height map (1 px = 1 mm). u = along travel (one wheel revolution), v = across (400 mm)
from PIL import Image, ImageDraw, ImageFilter
import math
L, Wd = 1571, 400
im = Image.new("L", (L, Wd), 128); d = ImageDraw.Draw(im)
# 24 chevron grousers -> grooves (dark)
for k in range(24):
    x0 = k*L/24
    for s in (-1, 1):
        for off in (0, L, -L):
            d.line([(x0 + off + 9, Wd/2 + s*48), (x0 + off + 45, Wd/2 + s*Wd/2)], fill=50, width=10)
# J P L in Morse along the centre line, raised (light)
code = ".--- .--. .-.."
x = 300
for ch in code:
    if ch == " ": x += 50; continue
    ln = 22 if ch == "." else 66
    d.rectangle([x, Wd/2 - 34, x + ln, Wd/2 + 34], fill=255)
    x += ln + 22
im = im.filter(ImageFilter.GaussianBlur(3))
im.save("track.png"); print("morse end", x)
