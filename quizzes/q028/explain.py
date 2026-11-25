# Animated explanation for the solution video of Quiz #28 (runway numbers). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

ASP = (40, 42, 46)
C = (480, 470)

def compass(k, a=1.0, r=300):
    k.circle(C, r, outline=GREY, w=3, a=a)
    for deg in range(0, 360, 10):
        rad = math.radians(deg - 90)
        r0 = r - (22 if deg % 90 == 0 else 12)
        k.line((C[0] + r0*math.cos(rad), C[1] + r0*math.sin(rad)), (C[0] + r*math.cos(rad), C[1] + r*math.sin(rad)), GREY, 3 if deg % 90 == 0 else 2, a=a)
    for deg, lab in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
        rad = math.radians(deg - 90)
        k.text((C[0] + (r + 40)*math.cos(rad), C[1] + (r + 40)*math.sin(rad) - 18), lab, 34, WHITE, a=a, anchor="ma")

def runway(k, a=1.0, l=420):
    # east-west strip through the centre
    k.rect((C[0] - l/2, C[1] - 34, C[0] + l/2, C[1] + 34), fill=ASP, outline=WHITE, w=2, a=a)
    for j in range(-3, 4):
        k.line((C[0] + j*50 - 14, C[1]), (C[0] + j*50 + 14, C[1]), WHITE, 3, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "27 = ABOUT 270°", GOLD, a=seg(t, 0, 0.4))
    compass(k, seg(t, 0.1, 0.6))
    runway(k, seg(t, 0.4, 0.8))
    v = seg(t, 1.0, 1.6)
    k.arrow((C[0] + 200, C[1] - 70), (C[0] - 200, C[1] - 70), GOLD, 6, prog=v)
    k.text((C[0] + 210, C[1] - 92), "27", 44, GOLD, a=v, anchor="la")
    w = seg(t, d*0.45, d*0.45 + 0.4)
    k.text((480, 842), "270° ÷ 10 = 27  →  WEST", 40, WHITE, a=w, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "OTHER END: +180°", BLUE, a=seg(t, 0, 0.4))
    compass(k, 1.0); runway(k, 1.0)
    k.arrow((C[0] + 200, C[1] - 70), (C[0] - 200, C[1] - 70), GOLD, 6, a=0.45)
    k.text((C[0] + 210, C[1] - 92), "27", 44, GOLD, a=0.45, anchor="la")
    v = seg(t, 0.6, 1.3)
    k.arrow((C[0] - 200, C[1] + 70), (C[0] + 200, C[1] + 70), BLUE, 6, prog=v)
    k.text((C[0] - 210, C[1] + 48), "09", 44, BLUE, a=v, anchor="ra")
    # sweep half a circle
    sw = seg(t, 1.4, 2.8)
    if sw > 0: k.arc(C, 230, 180, 180 + 180*sw, GREEN, 5)
    w = seg(t, d*0.5, d*0.5 + 0.4)
    k.text((480, 842), "90° ÷ 10 = 09  →  EAST", 40, WHITE, a=w, anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "THE MAGNETIC NORTH DRIFTS", RED, a=seg(t, 0, 0.4))
    compass(k, 0.5)
    # needle slowly turns a few degrees
    ang = math.radians(-90 + 8*seg(t, 0.8, d*0.6))
    tip = (C[0] + 240*math.cos(ang), C[1] + 240*math.sin(ang)); tail = (C[0] - 160*math.cos(ang), C[1] - 160*math.sin(ang))
    k.line(tail, C, GREY, 8); k.arrow(C, tip, RED, 8, head=30)
    k.circle(C, 12, fill=WHITE)
    v = seg(t, d*0.55, d*0.55 + 0.4)
    k.rect((260, 760, 700, 850), fill=ASP, outline=WHITE, w=2, r=10, a=v)
    k.text((390, 782), "27", 44, GREY, a=v, anchor="ma")
    k.text((480, 782), "→", 44, WHITE, a=v, anchor="ma")
    k.text((570, 782), "28", 44, GOLD, a=seg(t, d*0.7, d*0.7 + 0.4), anchor="ma")
    k.text((480, 180), "NEW NUMBERS ARE PAINTED", 36, GOLD, a=seg(t, d*0.75, d*0.75 + 0.4), anchor="ma")

SCENES = [scene0, scene1, scene2]
