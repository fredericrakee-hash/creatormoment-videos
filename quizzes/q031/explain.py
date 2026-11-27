# Animated explanation for the solution video of Quiz #31 (Taipei 101 tuned mass damper). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

GLASS = (40, 70, 70); BALL = (230, 170, 70)

def tower(k, base_x, lean, a=1.0, y0=820, h=640):
    """simple stacked-segment silhouette; lean = top offset in px (bends linearly)"""
    segs = 8; sh = h*0.62/segs; y = y0
    k.shape([(base_x - 90, y0), (base_x + 90, y0), (base_x + 70 + lean*0.15, y0 - h*0.2), (base_x - 70 + lean*0.15, y0 - h*0.2)], fill=GLASS, outline=WHITE, w=2, a=a)
    y = y0 - h*0.2
    for s in range(segs):
        f0 = (y0 - y)/h; f1 = (y0 - (y - sh))/h
        x0 = base_x + lean*f0; x1 = base_x + lean*f1
        k.shape([(x0 - 52, y), (x0 + 52, y), (x1 + 64, y - sh), (x1 - 64, y - sh)], fill=GLASS, outline=WHITE, w=2, a=a)
        y -= sh
    xt = base_x + lean*((y0 - y)/h)
    k.rect((xt - 30, y - h*0.1, xt + 30, y), fill=GLASS, outline=WHITE, w=2, a=a)
    k.line((xt, y - h*0.1), (xt + lean*0.05, y - h*0.18), WHITE, 3, a=a)
    return xt, y

def scene0(k, t, d):
    k.tag((60, 50), "IN A TYPHOON", RED, a=seg(t, 0, 0.4))
    sw = 26*math.sin(t*2.2)*seg(t, 0.4, 1.0)
    xt, yt = tower(k, 420, sw)
    for j in range(4):
        y = 260 + j*120; p = ((t*0.9 + j*0.3) % 1.0)
        k.arrow((40 + 120*p, y), (130 + 120*p, y), BLUE, 4, a=seg(t, 0.3, 0.8)*(1 - p))
    v = seg(t, 1.2, 1.6)
    k.arrow((xt - 70, yt + 60), (xt + 70, yt + 60), GOLD, 4, a=v)
    k.arrow((xt + 70, yt + 90), (xt - 70, yt + 90), GOLD, 4, a=v)
    k.text((640, 240), "THE TOP", 40, GOLD, a=v)
    k.text((640, 290), "SWAYS", 40, GOLD, a=v)
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((640, 380), "PEOPLE UP HERE", 30, WHITE, a=w)
    k.text((640, 420), "CAN FEEL IT", 30, WHITE, a=w)

def scene1(k, t, d):
    k.tag((60, 50), "A GIANT PENDULUM", GOLD, a=seg(t, 0, 0.4))
    ph = t*1.6
    bx = 40*math.sin(ph)*seg(t, 0.6, 1.2)            # building top moves
    k.rect((200 + bx, 140, 760 + bx, 820), outline=WHITE, w=3, a=1.0)
    k.text((480 + bx, 100), "BUILDING", 28, GREY, a=seg(t, 0.2, 0.6), anchor="ma")
    piv = (480 + bx, 200)
    ang = -0.35*math.sin(ph)*seg(t, 0.6, 1.2)       # ball lags the other way
    L = 380
    bc = (piv[0] + L*math.sin(ang), piv[1] + L*math.cos(ang))
    k.line(piv, bc, GREY, 4)
    k.circle(bc, 80, fill=BALL, outline=WHITE, w=2)
    v = seg(t, 1.4, 1.8)
    dirb = 1 if math.cos(ph) > 0 else -1
    k.arrow((480 + bx - 60*dirb, 760), (480 + bx + 60*dirb, 760), WHITE, 5, a=v)
    k.text((480 + bx, 780), "BUILDING", 24, WHITE, a=v, anchor="ma")
    k.arrow((bc[0] + 60*dirb, bc[1] - 120), (bc[0] - 60*dirb, bc[1] - 120), GOLD, 5, a=v)
    k.text((bc[0], bc[1] + 100), "660 t BALL", 28, GOLD, a=v, anchor="ma")
    w = seg(t, d*0.6, d*0.6 + 0.4)
    k.text((480, 470), "PULLS THE OTHER WAY", 34, GREEN, a=w, anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "TUNED MASS DAMPER", GREEN, a=seg(t, 0, 0.4))
    k.text((80, 150), "WITHOUT", 30, RED, a=seg(t, 0.2, 0.6))
    k.text((80, 470), "WITH THE BALL", 30, GREEN, a=seg(t, 0.8, 1.2))
    p1 = seg(t, 0.3, 2.3); p2 = seg(t, 0.9, 2.9)
    pts1 = [(80 + x*8, 300 - 90*math.exp(-x/120)*math.sin(x*0.25)) for x in range(101)]
    pts2 = [(80 + x*8, 620 - 90*math.exp(-x/18)*math.sin(x*0.25)) for x in range(101)]
    k.line((80, 300), (880, 300), GREY, 1, a=0.6); k.line((80, 620), (880, 620), GREY, 1, a=0.6)
    k.poly(pts1, RED, 4, prog=p1)
    k.poly(pts2, GREEN, 4, prog=p2)
    k.text((880, 730), "TIME →", 24, GREY, a=seg(t, 0.5, 0.9), anchor="ra", bold=False)
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((480, 790), "HYDRAULIC DAMPERS TURN THE MOTION INTO HEAT", 26, WHITE, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
