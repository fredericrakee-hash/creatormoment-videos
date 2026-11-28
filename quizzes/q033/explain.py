# Animated explanation for the solution video of Quiz #33 (bore evacuator). Drawn with pipeline/explain_kit.py.
import math, random
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

STEEL = (70, 78, 88); SLEEVE = (90, 100, 70); GAS = (255, 170, 90); FUME = (150, 145, 135)
Y = 440            # barrel centre line
def barrel(k, a=1.0, sleeve=True):
    k.rect((40, Y-40, 920, Y+40), fill=STEEL, outline=WHITE, w=2, a=a)
    k.rect((40, Y-28, 920, Y+28), fill=(18, 20, 26), a=a)          # the bore
    if sleeve:
        k.shape([(380, Y-40), (420, Y-110), (640, Y-110), (680, Y-40)], fill=SLEEVE, outline=WHITE, w=2, a=a)
        k.shape([(380, Y+40), (420, Y+110), (640, Y+110), (680, Y+40)], fill=SLEEVE, outline=WHITE, w=2, a=a)
        k.rect((420, Y-100, 640, Y-42), fill=(30, 34, 26), a=a)
        k.rect((420, Y+42, 640, Y+100), fill=(30, 34, 26), a=a)
    for s in (-1, 1):                                                   # holes angled towards the muzzle
        for hx in (470, 500):
            k.line((hx, Y + s*28), (hx + 22, Y + s*46), GOLD, 5, a=a)
    k.text((60, Y+130), "BREECH  ·  CREW", 24, GREY, a=a, bold=False)
    k.text((900, Y+130), "MUZZLE", 24, GREY, a=a, anchor="ra", bold=False)

def scene0(k, t, d):
    k.tag((60, 50), "THE SHOT", GOLD, a=seg(t, 0, 0.4))
    barrel(k)
    p = seg(t, 0.5, 2.2)
    x = lerp(80, 960, p)
    if p < 1: k.rect((x-60, Y-24, x, Y+24), fill=(200, 170, 90), r=6)
    fill = seg(t, 1.3, 2.6)
    for s in (-1, 1):
        k.rect((420, Y + (s < 0)*(-100) + (s > 0)*42, 640, Y + (s < 0)*(-42) + (s > 0)*100), fill=GAS, a=0.75*fill)
    k.text((530, 220), "HOT GAS FILLS THE SLEEVE", 30, GAS, a=seg(t, 1.8, 2.3), anchor="ma")
    k.text((530, 262), "UNDER PRESSURE", 26, GREY, a=seg(t, 2.1, 2.6), anchor="ma", bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "AFTER THE SHOT", BLUE, a=seg(t, 0, 0.4))
    barrel(k)
    r = random.Random(4)
    drain = seg(t, 0.4, d*0.8)
    for s in (-1, 1):
        k.rect((420, Y + (s < 0)*(-100) + (s > 0)*42, 640, Y + (s < 0)*(-42) + (s > 0)*100), fill=GAS, a=0.75*(1-drain))
    for j in range(40):                                  # jets towards the muzzle drag the fumes out
        ph = r.random(); p = (t*0.45 + ph) % 1.0
        x = lerp(500, 940, p); y = Y + r.uniform(-16, 16)
        k.circle((x, y), 5 + 4*p, fill=GAS if p < 0.25 else FUME, a=seg(t, 0.4, 0.8)*(1-p*0.6))
    for j in range(18):
        ph = r.random(); p = (t*0.35 + ph) % 1.0
        x = lerp(60, 940, p); y = Y + r.uniform(-18, 18)
        k.circle((x, y), 7, fill=FUME, a=seg(t, 0.6, 1.0)*0.8)
    k.arrow((560, 300), (860, 300), GOLD, 5, prog=seg(t, 0.8, 1.6))
    k.text((710, 230), "FUMES PULLED OUT THE FRONT", 28, GOLD, a=seg(t, 1.2, 1.7), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "INSIDE THE TURRET", GREEN, a=seg(t, 0, 0.4))
    v = seg(t, 0.3, 0.8)
    k.rect((80, 200, 440, 600), fill=(30, 36, 46), outline=WHITE, w=2, r=14, a=v)
    k.text((260, 230), "WITHOUT IT", 28, RED, a=v, anchor="ma")
    r = random.Random(7)
    for j in range(30):
        k.circle((r.uniform(110, 410), r.uniform(290, 570)), r.uniform(10, 22), fill=FUME, a=v*0.6)
    k.cross((260, 430), 50, RED, 9, a=seg(t, 0.8, 1.1))
    w = seg(t, d*0.35, d*0.35 + 0.5)
    k.rect((520, 200, 880, 600), fill=(30, 36, 46), outline=WHITE, w=2, r=14, a=w)
    k.text((700, 230), "WITH IT", 28, GREEN, a=w, anchor="ma")
    k.check((700, 430), 50, GREEN, 9, a=w, prog=seg(t, d*0.35 + 0.3, d*0.35 + 0.8))
    z = seg(t, d*0.65, d*0.65 + 0.4)
    k.text((480, 700), "BORE EVACUATOR", 40, GOLD, a=z, anchor="ma")
    k.text((480, 760), "a.k.a. fume extractor", 28, GREY, a=z, anchor="ma", bold=False)

SCENES = [scene0, scene1, scene2]
