# Animated explanation for the solution video of Quiz #32 (red anti-fouling hull paint). Drawn with pipeline/explain_kit.py.
import math, random
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HULLRED = (150, 30, 25); HULLTOP = (40, 50, 70); SEA = (20, 50, 75); BARN = (200, 195, 180); WEED = (70, 120, 60)

def hull(k, y_wl=330, a=1.0):
    k.rect((0, y_wl, 960, 880), fill=SEA, a=0.6*a)
    k.shape([(60, 180), (900, 180), (900, 640), (820, 720), (140, 720), (60, 640)], fill=HULLTOP, outline=WHITE, w=2, a=a)
    k.shape([(60, y_wl), (900, y_wl), (900, 640), (820, 720), (140, 720), (60, 640)], fill=HULLRED, outline=WHITE, w=2, a=a)
    k.line((60, y_wl), (900, y_wl), WHITE, 2, a=a)

def growth(k, frac, a=1.0, seed=3):
    r = random.Random(seed)
    for j in range(140):
        x = r.uniform(80, 880); y = r.uniform(350, 700); th = r.random()
        if th > frac: continue
        if r.random() < 0.6:
            k.circle((x, y), r.uniform(7, 14), fill=BARN, outline=(120, 115, 100), w=1, a=a)
        else:
            k.line((x, y), (x + r.uniform(-10, 10), y + r.uniform(20, 40)), WEED, 5, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "UNDER THE WATERLINE", BLUE, a=seg(t, 0, 0.4))
    hull(k)
    growth(k, seg(t, 0.5, d*0.5))
    k.text((480, 120), "BARNACLES · MUSSELS · WEED", 30, WHITE, a=seg(t, 0.8, 1.2), anchor="ma")
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.rect((180, 760, 780, 860), fill=(10, 12, 18), r=14, a=0.75*w)
    k.text((480, 775), "ROUGH HULL = MORE DRAG", 32, RED, a=w, anchor="ma")
    k.text((480, 818), "SLOWER · MORE FUEL", 26, GREY, a=w, anchor="ma", bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "ANTI-FOULING PAINT", GREEN, a=seg(t, 0, 0.4))
    hull(k)
    r = random.Random(9)
    v = seg(t, 0.6, 1.2)
    for j in range(26):
        x = r.uniform(100, 860); y0 = r.uniform(380, 680); ph = r.random()
        p = (t*0.5 + ph) % 1.0
        k.circle((x + 20*p, y0 + 60*p), 4 + 3*p, fill=(240, 150, 90), a=v*(1 - p))
    k.text((480, 120), "SLOWLY RELEASES COPPER", 32, GOLD, a=v, anchor="ma")
    # larva tries to settle and is turned away
    c = seg(t, 1.6, 3.0)
    lx = lerp(480, 300, c); ly = lerp(860, 560, c)
    k.circle((lx, ly), 10, fill=BARN, a=seg(t, 1.6, 1.8))
    k.cross((lx + 40, ly - 30), 22, RED, 6, a=seg(t, 2.8, 3.1))
    w = seg(t, d*0.65, d*0.65 + 0.4)
    k.text((480, 780), "CREATURES CAN'T SETTLE", 32, GREEN, a=w, anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "WHY RED?", GOLD, a=seg(t, 0, 0.4))
    v = seg(t, 0.3, 0.8)
    k.rect((140, 220, 420, 520), fill=(170, 40, 30), outline=WHITE, w=2, r=10, a=v)
    k.text((280, 540), "COPPER PAINT", 28, WHITE, a=v, anchor="ma")
    k.text((280, 580), "TRADITIONALLY RED", 24, GREY, a=v, anchor="ma", bold=False)
    w = seg(t, d*0.4, d*0.4 + 0.5)
    for j, col in enumerate(((30, 30, 34), (40, 70, 140), (150, 150, 150))):
        k.rect((560 + j*100, 300, 640 + j*100, 440), fill=col, outline=WHITE, w=2, r=8, a=w)
    k.text((710, 470), "OTHER COLOURS EXIST", 24, GREY, a=w, anchor="ma", bold=False)
    z = seg(t, d*0.7, d*0.7 + 0.4)
    k.text((480, 700), "MOST SHIPS KEEP THE CLASSIC RED", 32, GOLD, a=z, anchor="ma")
    k.check((480, 790), 30, GREEN, 7, a=z, prog=z)

SCENES = [scene0, scene1, scene2]
