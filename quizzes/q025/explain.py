# Animated explanation for the solution video of Quiz #25 (locomotive sanders). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

STEEL = (120, 110, 100); SAND = (214, 170, 100)
RY = 600          # rail top
WC = (430, 440)   # wheel centre
WR = 160

def rail(k, wet=0.0, a=1.0):
    k.rect((40, RY, 920, RY + 46), fill=(70, 66, 62), outline=WHITE, w=2, a=a)
    k.rect((300, RY + 46, 560, RY + 70), fill=(55, 52, 50), a=a)
    if wet > 0:
        k.rect((40, RY - 8, 920, RY), fill=(120, 190, 255, 255), a=a*wet*0.8)
        for x in (120, 250, 700, 830):
            k.shape([(x, RY - 8), (x + 30, RY - 22), (x + 60, RY - 8)], fill=(190, 90, 30), a=a*wet)

def wheel(k, ang, a=1.0, blur=0.0):
    c = WC
    k.circle(c, WR + 12, fill=(60, 58, 56), outline=WHITE, w=2, a=a)
    k.circle(c, WR, fill=STEEL, a=a)
    k.circle(c, 40, fill=(40, 40, 42), a=a)
    n = 6
    for i in range(n):
        th = ang + i*2*math.pi/n
        p = (c[0] + 100*math.cos(th), c[1] + 100*math.sin(th))
        k.circle(p, 22, fill=(30, 30, 32), a=a*(1 - 0.7*blur))
    if blur > 0:
        k.arc(c, 100, 0, 360, (30, 30, 32), 30, a=a*blur*0.5)

def scene0(k, t, d):
    k.tag((60, 50), "THE PROBLEM", RED, a=seg(t, 0, 0.4))
    rail(k, wet=seg(t, 0.3, 0.9))
    wheel(k, t*9.0, blur=0.7)
    v = seg(t, 0.8, 1.2)
    k.arc(WC, WR + 40, 200, 330, GOLD, 6, a=v)
    k.arrow((WC[0] + 120, WC[1] - 175), (WC[0] + 165, WC[1] - 120), GOLD, 6, a=v)
    k.text((80, 140), "WET RAIL + LEAVES", 36, BLUE, a=seg(t, 0.4, 0.8))
    w = seg(t, d*0.5, d*0.5 + 0.4)
    k.text((80, 200), "WHEEL SPINS, TRAIN STAYS", 36, RED, a=w)
    k.cross((800, 300), 34, RED, 8, a=w)

def scene1(k, t, d):
    k.tag((60, 50), "THE FIX: A SANDER", GOLD, a=seg(t, 0, 0.4))
    rail(k, wet=0.6)
    wheel(k, t*5.0, blur=0.4)
    # sand box + pipe
    k.rect((700, 120, 880, 230), fill=(50, 50, 55), outline=WHITE, w=2, a=seg(t, 0.2, 0.6))
    k.text((790, 160), "SAND", 26, SAND, a=seg(t, 0.2, 0.6), anchor="ma")
    k.poly([(760, 230), (760, 420), (650, 560)], (40, 40, 44), 18, prog=seg(t, 0.4, 1.0))
    k.poly([(760, 230), (760, 420), (650, 560)], GREY, 3, prog=seg(t, 0.4, 1.0))
    on = seg(t, 1.1, 1.4)
    for i in range(36):
        u = ((t*1.8 + i*0.618) % 1.0)
        x = lerp(650, 575, u) + ((i*37) % 13 - 6)*u; y = lerp(560, RY - 6, u) + ((i*53) % 11 - 5)*u
        k.circle((x, y), 4, fill=SAND, a=on)
    k.arrow((860, 300), (790, 300), BLUE, 5, a=seg(t, 1.0, 1.4))
    k.text((80, 140), "COMPRESSED AIR BLOWS", 34, BLUE, a=seg(t, 1.0, 1.4))
    k.text((80, 195), "DRY SAND UNDER THE WHEEL", 34, SAND, a=seg(t, 1.4, 1.8))

def scene2(k, t, d):
    k.tag((60, 50), "WHY IT WORKS", GREEN, a=seg(t, 0, 0.4))
    # zoom on the contact patch
    k.rect((40, 560, 920, 640), fill=(70, 66, 62), outline=WHITE, w=2)
    k.arc((480, -700), 1260, 60, 120, STEEL, 40)
    for i in range(14):
        x = 300 + i*28; crushed = seg(t, 0.6 + i*0.05, 0.9 + i*0.05)
        r = lerp(9, 5, crushed)
        k.circle((x, 552 + crushed*2), r, fill=SAND)
    k.text((480, 680), "GRAINS CRUSHED BETWEEN STEEL AND STEEL", 26, SAND, a=seg(t, 0.8, 1.2), anchor="ma", bold=False)
    v = seg(t, 1.4, 1.8)
    k.arrow((360, 400), (620, 400), GREEN, 8, prog=v, a=v)
    k.text((480, 320), "THE WHEEL CAN BITE", 38, GREEN, a=v, anchor="ma")
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.rect((180, 760, 780, 830), fill=(0, 0, 0, 150), outline=GOLD, w=2, r=18, a=w)
    k.text((480, 777), "HUNDREDS OF KG OF SAND ON BOARD", 28, GOLD, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
