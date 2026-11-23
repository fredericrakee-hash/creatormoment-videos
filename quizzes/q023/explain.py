# Animated explanation for the solution video of Quiz #23 (winglets). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

WINGC = (200, 205, 214)

def section(k, cx, cy, a=1.0, winglet=False):
    """front view of a wing (from ahead), tip on the right"""
    k.shape([(cx - 380, cy + 10), (cx + 220, cy - 30), (cx + 220, cy - 12), (cx - 380, cy + 34)], fill=WINGC, outline=WHITE, w=2, a=a)
    if winglet:
        k.shape([(cx + 205, cy - 30), (cx + 250, cy - 160), (cx + 266, cy - 158), (cx + 222, cy - 12)], fill=(230, 120, 90), outline=WHITE, w=2, a=a)

def swirl(k, c, r, t, col, a=1.0, n=3):
    for j in range(n):
        rr = r*(1 - j*0.28)
        a0 = t*220 + j*120
        k.arc(c, rr, a0, a0 + 250, col, 4, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "HIGH PRESSURE BELOW, LOW ABOVE", GOLD, a=seg(t, 0, 0.4))
    section(k, 420, 440, seg(t, 0.1, 0.5))
    k.text((180, 330), "LOW", 36, BLUE, a=seg(t, 0.5, 0.9))
    k.text((180, 520), "HIGH", 36, RED, a=seg(t, 0.7, 1.1))
    # air curling around the tip
    p = seg(t, 1.2, 2.2)
    k.poly([(560, 520), (680, 500), (720, 430), (690, 370), (630, 360)], GOLD, 5, prog=p)
    k.arrow((650, 362), (610, 366), GOLD, 5, prog=seg(t, 2.1, 2.3), head=16)
    v = seg(t, d*0.5, d*0.5 + 0.5)
    swirl(k, (760, 440), 90, t, WHITE, a=v)
    k.text((760, 580), "WINGTIP VORTEX", 32, WHITE, a=v, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "INDUCED DRAG", RED, a=seg(t, 0, 0.4))
    # side view: plane silhouette + trailing spiral pulling back
    k.shape([(560, 400), (880, 400), (900, 420), (880, 440), (560, 440)], fill=WINGC, outline=WHITE, w=2)
    k.shape([(700, 400), (640, 330), (660, 330), (740, 400)], fill=WINGC, outline=WHITE, w=2)
    pts = []
    for i in range(80):
        x = 560 - i*6; r = 10 + i*0.7
        pts.append((x, 420 + r*math.sin(i*0.35 - t*6)))
    k.poly(pts, WHITE, 3, prog=seg(t, 0.3, 1.3))
    k.arrow((520, 520), (300, 520), RED, 7, prog=seg(t, 1.3, 1.9), head=22)
    k.text((410, 545), "HOLDS THE PLANE BACK", 30, RED, a=seg(t, 1.5, 1.9), anchor="ma")
    v = seg(t, d*0.55, d*0.55 + 0.4)
    k.rect((180, 660, 780, 800), fill=(10, 13, 20, 210), r=18, a=v)
    k.text((480, 690), "ENGINES WORK HARDER", 34, WHITE, a=v, anchor="ma")
    k.text((480, 740), "→ MORE FUEL BURNED", 30, GOLD, a=v, anchor="ma", bold=False)

def scene2(k, t, d):
    k.tag((60, 50), "THE WINGLET WEAKENS IT", GREEN, a=seg(t, 0, 0.4))
    k.text((250, 130), "WITHOUT", 28, GREY, a=seg(t, 0.2, 0.6), anchor="ma")
    k.text((710, 130), "WITH WINGLET", 28, GREEN, a=seg(t, 0.2, 0.6), anchor="ma")
    # left: plain tip, big swirl
    k.shape([(40, 330), (330, 300), (330, 318), (40, 350)], fill=WINGC, outline=WHITE, w=2)
    swirl(k, (370, 320), 95, t, RED, a=seg(t, 0.3, 0.7))
    # right: winglet, small swirl
    k.shape([(510, 330), (800, 300), (800, 318), (510, 350)], fill=WINGC, outline=WHITE, w=2)
    k.shape([(790, 300), (825, 200), (838, 202), (806, 318)], fill=(230, 120, 90), outline=WHITE, w=2)
    swirl(k, (860, 210), 40, t, GREEN, a=seg(t, 0.5, 0.9))
    # fuel bars
    v = seg(t, 1.2, 2.0)
    k.text((480, 470), "FUEL BURN", 28, GREY, a=v, anchor="ma", bold=False)
    k.rect((150, 520, 150 + 660*v, 570), fill=RED, a=v)
    k.rect((150, 600, 150 + 627*v, 650), fill=GREEN, a=v)
    k.text((810, 665), "UP TO ~5% LESS", 30, GREEN, a=seg(t, 2.0, 2.4), anchor="ra")
    w = seg(t, d*0.6, d*0.6 + 0.4)
    k.text((480, 760), "BILLIONS OF LITRES SAVED", 36, GOLD, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
