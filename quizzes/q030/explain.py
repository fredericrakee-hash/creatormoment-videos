# Animated explanation for the solution video of Quiz #30 (gas-fired switch heaters). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

RAIL = (170, 175, 185); SNOW = (225, 232, 242); FIRE = (255, 140, 40)

def track(k, a=1.0, gap=0.0, closed=1.0):
    # top view: main line left->right, diverging line curving up; points near x=260
    for y in (520, 620):
        k.line((40, y), (920, y), RAIL, 6, a=a)
    pts1 = [(260 + i*20, 520 - (i*20)**2/900) for i in range(34)]
    k.poly(pts1, RAIL, 6, a=a)
    # movable point blade: from (260,620) towards either the stock rail or open
    tip_y = lerp(612, 560, closed)
    k.line((260, tip_y + gap), (520, 600), GOLD, 7, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "A SWITCH (TOP VIEW)", GOLD, a=seg(t, 0, 0.4))
    v = seg(t, 0.1, 0.6)
    sw = 0.5 + 0.5*math.sin(t*1.6)
    track(k, a=v, closed=sw)
    w = seg(t, d*0.35, d*0.35 + 0.4)
    k.text((300, 700), "MOVABLE POINTS", 36, GOLD, a=w)
    k.arrow((280, 690), (280, 640), GOLD, 4, prog=w, a=w)
    z = seg(t, d*0.6, d*0.6 + 0.4)
    k.text((480, 200), "THEY SEND THE TRAIN", 34, WHITE, a=z, anchor="ma")
    k.text((480, 245), "ONTO THE RIGHT TRACK", 34, WHITE, a=z, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "SNOW AND ICE", BLUE, a=seg(t, 0, 0.4))
    track(k, closed=0.55)
    v = seg(t, 0.3, 1.2)
    for j in range(7):
        x = 250 + j*18; y = 575 + 8*math.sin(j*1.7)
        k.circle((x, y), 16*v, fill=SNOW, a=v)
    w = seg(t, 1.4, 1.8)
    k.cross((380, 440), 34, RED, 8, a=w)
    k.text((440, 420), "CAN'T CLOSE", 36, RED, a=w)
    z = seg(t, d*0.55, d*0.55 + 0.4)
    k.circle((780, 300), 34, fill=(255, 60, 50), a=z); k.rect((760, 260, 800, 400), outline=GREY, w=3, a=z)
    k.text((780, 420), "SIGNAL: STOP", 30, RED, a=z, anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "GAS-FIRED SWITCH HEATERS", GREEN, a=seg(t, 0, 0.4))
    k.clip(0.5, (0, 0, 960, 880), dim=0.35)
    v = seg(t, 0.4, 1.0)
    for y in (300, 360):
        for j in range(16):
            x = 140 + j*44
            h = 26 + 10*math.sin(t*9 + j*1.3 + y)
            k.line((x, y), (x, y - h*v), FIRE, 8, a=v)
    w = seg(t, 1.4, 1.8)
    k.text((480, 430), "MELT THE SNOW AND ICE", 36, GREEN, a=w, anchor="ma")
    k.check((480, 500), 26, GREEN, 7, a=w, prog=w)
    z = seg(t, d*0.45, d*0.45 + 0.4)
    k.text((480, 600), "THE TRACKS AREN'T ON FIRE", 32, WHITE, a=z, anchor="ma")
    y_ = seg(t, d*0.7, d*0.7 + 0.4)
    k.tag((300, 680), "NEWER: ELECTRIC HEATERS", BLUE, a=y_, size=28)

SCENES = [scene0, scene1, scene2]
