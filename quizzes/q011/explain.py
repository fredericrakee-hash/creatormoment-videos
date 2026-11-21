# Animated explanation for the solution video of Quiz #11 (launch pad water deluge). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

def scene0(k, t, d):
    k.tag((60, 50), "HOW LOUD?", GOLD, a=seg(t, 0, 0.4))
    rows = [("LOUD CONCERT", 110, 0.6, WHITE), ("JET ENGINE, UP CLOSE", 140, 1.4, WHITE), ("SLS ROCKET AT LIFTOFF", 176, 2.4, RED)]
    for i, (name, db, ts, col) in enumerate(rows):
        y = 190 + i*190; g = seg(t, ts, ts + 1.0)
        k.text((70, y), name, 30, WHITE, a=seg(t, ts, ts + 0.3), bold=False)
        wmax = 820*(db - 60)/(180 - 60)
        k.rect((70, y + 50, 70 + 820, y + 110), fill=(255, 255, 255, 25), r=12, a=seg(t, ts, ts + 0.3))
        k.rect((70, y + 50, 70 + max(1, wmax*g), y + 110), fill=col if i < 2 else RED, r=12, a=seg(t, ts, ts + 0.3))
        k.text((70 + wmax*g - 16, y + 62), f"{int(round(db*g))} dB" if g > 0.2 else "", 34, (12, 14, 20), anchor="ra", shadow=False)
    k.text((480, 790), "+10 dB  ≈  10× MORE SOUND ENERGY", 30, GOLD, a=seg(t, 3.6, 4.0), anchor="ma", bold=False)

def rocket(k, x, y, a=1.0):
    k.rect((x - 30, y - 330, x + 30, y), fill=(225, 220, 210), r=6, a=a)
    k.shape([(x - 30, y - 330), (x, y - 400), (x + 30, y - 330)], fill=(225, 220, 210), a=a)
    for s in (-1, 1):
        k.rect((x + s*48 - 12, y - 250, x + s*48 + 12, y), fill=(240, 240, 240), r=6, a=a)
    k.rect((x - 30, y - 200, x + 30, y - 150), fill=(200, 110, 40), a=a)

def scene1(k, t, d):
    half = d*0.42
    pad = 600; cx = 420
    k.rect((40, pad, 920, pad + 40), fill=(120, 120, 125))
    k.rect((cx - 70, pad, cx + 70, pad + 40), fill=(20, 20, 24))             # flame trench opening
    rocket(k, cx, pad - 10)
    k.rect((700, 120, 740, pad), fill=(90, 95, 105)); k.rect((740, 300, 760, 312), fill=(90, 95, 105))  # tower
    fl = 0.8 + 0.2*math.sin(t*40)
    k.shape([(cx - 60, pad - 8), (cx + 60, pad - 8), (cx + 30*fl, pad + 120*fl), (cx - 30*fl, pad + 120*fl)], fill=(255, 190, 90))
    water = seg(t, half, half + 0.8)
    # pressure waves: bounce off the pad, hit the rocket and the tower
    for i in range(5):
        r = ((t*180 + i*80) % 400) + 20
        amp = (1 - r/420)*(1 - 0.85*water)
        k.arc((cx, pad), r, 200, 340, RED if water < 0.5 else (255, 160, 140), 6, a=amp)
    k.text((60, 60), "PRESSURE WAVES", 34, RED, a=seg(t, 0.6, 1.0)*(1 - water))
    k.text((60, 105), "SHAKE THE ROCKET", 34, RED, a=seg(t, 1.2, 1.6)*(1 - water))
    if water > 0:
        for i in range(70):
            u = ((t*1.6 + i*0.137) % 1.0)
            for side in (-1, 1):
                x0 = cx + side*360; xx = lerp(x0, cx + side*40, u); yy = pad - 40 - 120*math.sin(math.pi*u) + (i % 5)*6
                k.circle((xx, yy), 5, fill=BLUE, a=water*0.9)
        k.text((60, 60), "WATER SOAKS UP", 34, BLUE, a=water)
        k.text((60, 105), "THE ENERGY", 34, BLUE, a=water)
    # noise meter
    lvl = 1 - 0.6*water
    k.text((860, 380), "NOISE", 24, WHITE, anchor="ma", bold=False)
    k.rect((830, 410, 890, 580), fill=(0, 0, 0, 150), outline=WHITE, w=2, r=10)
    k.rect((838, 572 - 155*lvl, 882, 572), fill=RED if lvl > 0.6 else GREEN, r=6)

def scene2(k, t, d):
    k.clip(0.62 + 0.3*min(1, t/max(d, 0.1)), box=(0, 0, 960, 880), dim=0.15)
    k.tag((60, 50), "THE BIG WHITE CLOUDS", GOLD, a=seg(t, 0, 0.4))
    a = seg(t, 1.2, 1.7)
    k.rect((180, 700, 780, 800), fill=(0, 0, 0, 170), r=24, a=a)
    k.text((480, 722), "MOSTLY WATER  →  STEAM", 44, WHITE, a=a, anchor="ma")
    k.arrow((480, 690), (520, 560), GOLD, 5, prog=seg(t, 1.6, 2.2))

SCENES = [scene0, scene1, scene2]
