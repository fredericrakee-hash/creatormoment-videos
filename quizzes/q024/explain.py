# Animated explanation for the solution video of Quiz #24 (shark fin antenna). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

PAINT = (150, 30, 35); PCB = (30, 110, 70)

def fin_outline(k, a=1.0, ghost=False):
    pts = [(160, 640), (300, 560), (480, 440), (640, 330), (720, 310), (760, 360), (790, 640)]
    if ghost: k.poly(pts, WHITE, 3, a=a, dash=(14, 10))
    else: k.shape(pts, fill=PAINT, outline=WHITE, w=2, a=a)
    k.rect((120, 640, 840, 670), fill=(60, 62, 70), a=a)
    k.text((480, 700), "CAR ROOF", 24, GREY, a=a, anchor="ma", bold=False)

def scene0(k, t, d):
    k.tag((60, 50), "LOOK INSIDE THE FIN", GOLD, a=seg(t, 0, 0.4))
    cover = 1 - seg(t, 0.6, 1.4)
    fin_outline(k, a=max(cover, 0.0))
    fin_outline(k, a=1 - cover, ghost=True)
    v = seg(t, 1.2, 1.8)
    k.rect((220, 590, 760, 630), fill=PCB, outline=WHITE, w=2, a=v)
    k.text((490, 600), "CIRCUIT BOARD", 22, WHITE, a=v, anchor="ma", bold=False)
    # three antenna elements popping up
    for j, (x, h, lab) in enumerate(((330, 90, "1"), (500, 180, "2"), (660, 260, "3"))):
        w_ = seg(t, 1.8 + j*0.35, 2.2 + j*0.35)
        k.line((x, 590), (x, 590 - h*w_), GOLD, 7, a=w_)
        k.circle((x, 590 - h*w_), 9, fill=GOLD, a=w_)
    k.text((480, 150), "SEVERAL ANTENNAS", 40, GOLD, a=seg(t, d*0.55, d*0.55 + 0.4), anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "WHAT THEY PICK UP", BLUE, a=seg(t, 0, 0.4))
    fin_outline(k, a=0.35, ghost=True)
    k.rect((220, 590, 760, 630), fill=PCB, outline=WHITE, w=2)
    items = (("FM + DIGITAL RADIO", 330, 500, 0.3), ("GPS NAVIGATION", 500, 410, 1.4), ("MOBILE DATA", 660, 330, 2.6))
    for j, (lab, x, y, t0) in enumerate(items):
        w_ = seg(t, t0, t0 + 0.5)
        k.line((x, 590), (x, y), GOLD, 7, a=0.6 + 0.4*w_)
        for r in range(3):
            rr = 30 + ((t*60 + r*40) % 120)
            k.arc((x, y), rr, 200, 340, BLUE, 3, a=w_*(1 - (rr - 30)/120))
        k.text((80 if j != 2 else 880, 170 + j*70), lab, 34, WHITE if j != 1 else GOLD, a=w_, anchor="la" if j != 2 else "ra")

def scene2(k, t, d):
    k.tag((60, 50), "WHY A PLASTIC FIN?", GREEN, a=seg(t, 0, 0.4))
    # left: waves pass through plastic
    k.shape([(80, 560), (180, 470), (300, 400), (340, 430), (360, 560)], fill=PAINT, outline=WHITE, w=2, a=seg(t, 0.2, 0.6))
    for r in range(4):
        x = 420 - ((t*120 + r*60) % 360)
        k.line((x, 360), (x - 20, 600), BLUE, 3, a=seg(t, 0.4, 0.8)*0.8)
    k.check((220, 680), 28, GREEN, 7, a=seg(t, 0.8, 1.2), prog=seg(t, 0.8, 1.3))
    k.text((265, 660), "SIGNALS PASS", 28, GREEN, a=seg(t, 0.8, 1.2))
    # right: old metal rod
    v = seg(t, d*0.45, d*0.45 + 0.4)
    k.line((700, 600), (800, 260), GREY, 6, a=v)
    k.rect((660, 600, 860, 620), fill=(60, 62, 70), a=v)
    k.text((760, 200), "OLD METAL ROD", 28, GREY, a=v, anchor="ma")
    w = seg(t, d*0.65, d*0.65 + 0.4)
    k.cross((540, 700), 22, RED, 6, a=w)
    k.text((575, 682), "WHISTLES, SNAPS OFF", 24, RED, a=w)

SCENES = [scene0, scene1, scene2]
