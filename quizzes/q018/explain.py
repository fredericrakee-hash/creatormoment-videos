# Animated explanation for the solution video of Quiz #18 (decoy flares). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HOT = (255, 150, 60); FLARE = (255, 240, 200)

def plane(k, x, y, a=1.0, s=1.0):
    # simple side-view transport plane silhouette, nose to the right
    k.shape([(x - 150*s, y - 6*s), (x + 120*s, y - 14*s), (x + 160*s, y), (x + 120*s, y + 16*s), (x - 150*s, y + 10*s)],
            fill=(70, 78, 90), outline=WHITE, w=2, a=a)
    k.shape([(x - 150*s, y - 6*s), (x - 170*s, y - 60*s), (x - 130*s, y - 60*s), (x - 110*s, y - 8*s)], fill=(70, 78, 90), outline=WHITE, w=2, a=a)
    k.shape([(x - 20*s, y - 4*s), (x + 20*s, y - 4*s), (x - 40*s, y + 60*s), (x - 70*s, y + 60*s)], fill=(60, 66, 78), outline=WHITE, w=2, a=a)

def missile(k, x, y, ang, a=1.0):
    dx, dy = math.cos(ang), math.sin(ang)
    k.line((x - 50*dx, y - 50*dy), (x + 20*dx, y + 20*dy), WHITE, 7, a=a)
    k.circle((x + 22*dx, y + 22*dy), 6, fill=RED, a=a)
    k.line((x - 50*dx, y - 50*dy), (x - 120*dx, y - 120*dy), GREY, 3, a=a*0.6)

def scene0(k, t, d):
    k.tag((60, 50), "HEAT-SEEKING MISSILE", RED, a=seg(t, 0, 0.4))
    v = seg(t, 0.2, 0.7)
    plane(k, 620, 300, a=v)
    for j, ex in enumerate((560, 640)):
        r = 22 + 6*math.sin(t*6 + j)
        k.circle((ex - 30, 350), r, fill=HOT, a=v*0.8)
    p = seg(t, 0.8, d*0.85)
    mx, my = lerp(140, 520, p), lerp(800, 400, p)
    missile(k, mx, my, math.atan2(400 - 800, 520 - 140), a=seg(t, 0.6, 1.0))
    w = seg(t, d*0.45, d*0.45 + 0.4)
    k.arrow((mx + 40, my - 40), (560, 370), RED, 3, prog=w, a=w)
    k.text((480, 150), "IT STEERS TOWARDS THE HOTTEST SPOT", 34, WHITE, a=w, anchor="ma")
    k.tag((640, 420), "HOT ENGINES", HOT, a=w, size=24)

def scene1(k, t, d):
    k.tag((60, 50), "DECOY FLARE", GREEN, a=seg(t, 0, 0.4))
    px = lerp(620, 760, seg(t, 0, d))
    plane(k, px, 260)
    f = seg(t, 0.5, d*0.5)
    fx, fy = lerp(px - 40, 360, f), lerp(320, 560, f)
    k.circle((fx, fy), 18 + 30*f, fill=FLARE, a=seg(t, 0.4, 0.7))
    k.circle((fx, fy), 50 + 30*f, fill=HOT, a=seg(t, 0.4, 0.7)*0.35)
    # missile turns towards the flare
    p = seg(t, 0.8, d*0.9)
    mx, my = lerp(120, fx - 60, p), lerp(840, fy + 120, p)
    missile(k, mx, my, math.atan2(fy - my, fx - mx), a=1.0)
    # temperature bars
    b = seg(t, 1.0, 1.8)
    k.rect((620, 560, 660, 760), outline=GREY, w=2, a=b)
    k.rect((620, 760 - 70*b, 660, 760), fill=HOT, a=b)
    k.text((640, 780), "ENGINE", 24, GREY, a=b, anchor="ma", bold=False)
    k.rect((760, 560, 800, 760), outline=GREY, w=2, a=b)
    k.rect((760, 760 - 190*b, 800, 760), fill=FLARE, a=b)
    k.text((780, 780), "FLARE", 24, WHITE, a=b, anchor="ma")
    k.text((710, 510), "MUCH HOTTER", 30, GOLD, a=seg(t, 1.8, 2.2), anchor="ma")
    w = seg(t, d*0.7, d*0.7 + 0.4)
    k.text((480, 150), "THE MISSILE CHASES THE FLARE", 36, GREEN, a=w, anchor="ma")
    k.check((480, 215), 24, GREEN, 7, a=w, prog=w)

def scene2(k, t, d):
    k.tag((60, 50), "JUST ONE LAYER", BLUE, a=seg(t, 0, 0.4))
    k.clip(0.55, (0, 0, 960, 880), dim=0.45)
    items = [("FLARES", GREEN), ("MANEUVERS", BLUE), ("WARNING SENSORS", BLUE), ("JAMMERS", BLUE)]
    for j, (lab, col) in enumerate(items):
        z = seg(t, d*0.35 + j*0.35, d*0.35 + j*0.35 + 0.3)
        k.rect((220, 300 + j*110, 740, 380 + j*110), fill=(20, 24, 32), outline=col, w=3, r=10, a=z*0.9)
        k.text((480, 322 + j*110), lab, 34, col, a=z, anchor="ma")
    w = seg(t, 0.3, 0.8)
    k.text((480, 170), "FIRED EARLY, JUST IN CASE", 34, WHITE, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
