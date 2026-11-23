# Animated explanation for the solution video of Quiz #13 (zigzag contact wire / stagger). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

CARBON = (60, 62, 68); METAL = (190, 195, 205); COPPER = (215, 140, 80)

def strip(k, cx=480, y=520, a=1.0, wear=None):
    """front view of the pantograph head: horns + carbon strip"""
    k.poly([(cx - 380, y + 40), (cx - 340, y), (cx + 340, y), (cx + 380, y + 40)], METAL, 6, a=a)
    k.rect((cx - 300, y - 6, cx + 300, y + 22), fill=CARBON, outline=WHITE, w=2, a=a)
    k.line((cx - 200, y + 22), (cx, y + 200), METAL, 8, a=a)
    k.line((cx + 200, y + 22), (cx, y + 200), METAL, 8, a=a)
    if wear is not None:
        x0, x1, depth = wear
        k.rect((x0, y - 6, x1, y - 6 + depth), fill=(15, 15, 18), a=a)

def scene0(k, t, d):
    k.tag((60, 50), "PANTOGRAPH ON THE ROOF", GOLD, a=seg(t, 0, 0.4))
    a = seg(t, 0.1, 0.6)
    strip(k, a=a)
    # train roof
    k.rect((120, 720, 840, 760), fill=(120, 125, 135), a=a)
    k.text((480, 780), "TRAIN ROOF", 24, GREY, a=a, anchor="ma", bold=False)
    # wire cross-section touching the strip
    k.circle((480, 500), 14, fill=COPPER, outline=WHITE, w=2, a=seg(t, 0.6, 1.0))
    k.text((480, 420), "CONTACT WIRE", 28, COPPER, a=seg(t, 0.7, 1.1), anchor="ma")
    k.arrow((760, 420), (700, 510), GOLD, 4, prog=seg(t, 1.2, 1.7), head=16)
    k.text((770, 380), "CARBON STRIP", 30, WHITE, a=seg(t, 1.2, 1.6), anchor="ma")
    # tiny sliding sparks
    if t > 1.8:
        for i in range(5):
            ph = (t*2 + i*0.2) % 1.0
            k.circle((480 + 30*math.cos(i*1.3)*ph, 500 - 20*ph), 3, fill=(255, 230, 150), a=1 - ph)

def scene1(k, t, d):
    k.tag((60, 50), "STRAIGHT WIRE", RED, a=seg(t, 0, 0.4))
    dep = 4 + 30*seg(t, 0.8, d - 0.6)
    strip(k, wear=(462, 498, dep))
    k.circle((480, 500), 14, fill=COPPER, outline=WHITE, w=2)
    k.text((480, 300), "ALWAYS THE SAME SPOT", 36, RED, a=seg(t, 0.4, 0.8), anchor="ma")
    k.arrow((480, 350), (480, 470), RED, 5, prog=seg(t, 0.5, 1.0), head=18)
    v = seg(t, d*0.6, d*0.6 + 0.4)
    k.text((480, 800), "A GROOVE WEARS IN", 36, WHITE, a=v, anchor="ma")
    k.cross((800, 300), 34, RED, 8, a=v)

def scene2(k, t, d):
    k.tag((60, 50), "ZIGZAG = STAGGER", GREEN, a=seg(t, 0, 0.4))
    # top view: track + wire zigzag between masts
    k.rect((100, 120, 860, 140), fill=GREY, a=0.6)
    k.rect((100, 300, 860, 320), fill=GREY, a=0.6)
    k.text((480, 80), "VIEW FROM ABOVE", 24, GREY, anchor="ma", bold=False)
    pts = [(100 + i*190, 220 + (60 if i % 2 else -60)) for i in range(5)]
    k.poly(pts, COPPER, 5, prog=seg(t, 0.3, 1.3))
    for x, y in pts:
        k.circle((x, y), 8, fill=WHITE, a=seg(t, 0.3, 0.7))
    k.text((870, 335), "±20–30 cm", 30, GOLD, a=seg(t, 1.0, 1.4), anchor="ra")
    # moving contact point on the strip spreads wear evenly
    ph = math.sin(t*1.6)
    x = 480 + 200*ph
    strip(k, y=560, wear=(200, 760, int(6*seg(t, 1.5, d - 0.5))))
    k.circle((x, 540), 14, fill=COPPER, outline=WHITE, w=2)
    k.arrow((480, 640), (280, 640), BLUE, 4, prog=seg(t, 1.2, 1.6), head=14)
    k.arrow((480, 640), (680, 640), BLUE, 4, prog=seg(t, 1.2, 1.6), head=14)
    v = seg(t, d*0.6, d*0.6 + 0.4)
    k.check((240, 820), 30, GREEN, 8, a=v, prog=v)
    k.text((290, 800), "EVEN WEAR, LONGER LIFE", 34, GREEN, a=v)

SCENES = [scene0, scene1, scene2]
