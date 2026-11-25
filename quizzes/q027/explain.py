# Animated explanation for the solution video of Quiz #27 (submarine anechoic tiles). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HULL = (40, 42, 48); SEA = (18, 40, 60)

def sub(k, x, y, s=1.0, a=1.0, tiles=False):
    k.shape([(x - 200*s, y), (x - 160*s, y - 38*s), (x + 150*s, y - 38*s), (x + 205*s, y - 8*s), (x + 205*s, y + 8*s), (x + 150*s, y + 38*s), (x - 160*s, y + 38*s)],
            fill=HULL, outline=WHITE if not tiles else GOLD, w=2, a=a)
    k.rect((x + 20*s, y - 85*s, x + 80*s, y - 38*s), fill=HULL, outline=WHITE if not tiles else GOLD, w=2, r=8, a=a)
    if tiles:
        for j in range(-7, 8):
            k.line((x + j*22*s, y - 36*s), (x + j*22*s, y + 36*s), (70, 72, 80), 1, a=a)

def ship(k, x, y, a=1.0):
    k.shape([(x - 90, y - 20), (x + 90, y - 20), (x + 70, y + 12), (x - 70, y + 12)], fill=(90, 95, 105), outline=WHITE, w=2, a=a)
    k.rect((x - 30, y - 50, x + 20, y - 20), fill=(90, 95, 105), outline=WHITE, w=2, a=a)

def water(k, a=1.0):
    k.rect((0, 260, 960, 880), fill=SEA + (150,), a=a)
    k.waves(0, 960, 260, 5, 10, BLUE, 3, a=a)

def ping(k, t, src, dst, col, a, t0, speed=1.2, back=True, back_a=1.0):
    # outgoing arc travelling from src towards dst, then echo back
    L = math.dist(src, dst); u = (t - t0)*speed
    if 0 < u < 1:
        p = (lerp(src[0], dst[0], u), lerp(src[1], dst[1], u))
        k.arc(p, 46, 20, 160, col, 5, a=a)
    if back and 1 < u < 2:
        p = (lerp(dst[0], src[0], u - 1), lerp(dst[1], src[1], u - 1))
        k.arc(p, 46, 200, 340, col, 5, a=a*back_a)

def scene0(k, t, d):
    k.tag((60, 50), "HOW SONAR FINDS A SUBMARINE", GOLD, a=seg(t, 0, 0.4))
    water(k, seg(t, 0.1, 0.5))
    ship(k, 480, 250, seg(t, 0.3, 0.7))
    sub(k, 480, 680, 1.0, seg(t, 0.5, 0.9))
    for n in range(3):
        ping(k, t, (480, 280), (480, 630), BLUE, 1.0, 1.0 + n*2.2, 0.9)
    v = seg(t, 1.0, 1.4)
    k.text((80, 360), "PING", 34, BLUE, a=v)
    w = seg(t, 2.2, 2.6)
    k.text((880, 360), "ECHO", 34, GOLD, a=w, anchor="ra")
    k.arrow((800, 560), (800, 400), GOLD, 4, prog=w)

def scene1(k, t, d):
    k.tag((60, 50), "RUBBER TILES WITH AIR POCKETS", GREEN, a=seg(t, 0, 0.4))
    # big cut-away of one tile: steel hull at bottom, rubber tile with voids
    k.rect((120, 560, 840, 640), fill=(110, 115, 125), outline=WHITE, w=2, a=seg(t, 0.1, 0.5))
    k.text((480, 600), "STEEL HULL", 26, (20, 22, 28), a=seg(t, 0.1, 0.5), anchor="mm", shadow=False)
    v = seg(t, 0.4, 0.9)
    k.rect((120, 420, 840, 560), fill=(22, 22, 26), outline=GOLD, w=2, a=v)
    for j in range(26):
        cx = 150 + (j*97) % 660; cy = 450 + (j*37) % 90
        k.circle((cx, cy), 7 + (j % 3)*3, fill=(60, 62, 70), a=v)
    k.text((860, 395), "RUBBER TILE", 26, GOLD, a=v, anchor="ra", bold=False)
    # incoming waves get absorbed
    for n in range(4):
        u = ((t - 1.0)*0.8 - n*0.25) % 1.4
        if t < 1.0 or u > 1.0: continue
        y = lerp(140, 420, u)
        k.arc((480, y), 120, 30, 150, BLUE, 5, a=1 - u*0.6)
    w = seg(t, d*0.45, d*0.45 + 0.4)
    k.text((480, 180), "PING SOAKED UP", 40, GREEN, a=w, anchor="ma")
    z = seg(t, d*0.72, d*0.72 + 0.4)
    k.text((480, 740), "ENGINE NOISE MUFFLED", 34, WHITE, a=z, anchor="ma")
    for n in range(3):
        u = ((t*0.9) + n*0.33) % 1.0
        k.arc((480, 640), 40 + u*120, 60, 120, GREY, 3, a=z*(1 - u)*0.8)

def scene2(k, t, d):
    k.tag((60, 50), "ANECHOIC = WITHOUT ECHO", BLUE, a=seg(t, 0, 0.4))
    water(k, 1.0)
    ship(k, 480, 250, 1.0)
    sub(k, 480, 680, 1.0, 1.0, tiles=True)
    ping(k, t, (480, 280), (480, 630), BLUE, 1.0, 0.4, 0.9, back=True, back_a=0.18)
    v = seg(t, 2.0, 2.4)
    k.text((880, 360), "ALMOST NO ECHO", 32, GREEN, a=v, anchor="ra")
    k.check((830, 420), 22, GREEN, 6, a=v, prog=v)
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((480, 810), "LOST TILES? NEW ONES ARE GLUED ON", 30, WHITE, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
