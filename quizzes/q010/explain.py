# Animated explanation for the solution video of Quiz #10 (bridge expansion joint). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HOT, COLD = (255, 120, 70), (110, 180, 255)

def thermo(k, x, y, temp, a=1.0):
    """temp 0 (cold) .. 1 (hot)"""
    col = tuple(int(lerp(c, h, temp)) for c, h in zip(COLD, HOT))
    k.rect((x - 16, y, x + 16, y + 200), fill=(0, 0, 0, 160), outline=WHITE, w=2, r=16, a=a)
    k.circle((x, y + 214), 28, fill=col, outline=WHITE, w=2, a=a)
    h = lerp(30, 185, temp)
    k.rect((x - 8, y + 200 - h, x + 8, y + 214), fill=col, r=8, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "HEAT MAKES THINGS GROW", GOLD, a=seg(t, 0, 0.4))
    # temperature cycles cold -> hot -> cold
    ph = 0.5 - 0.5*math.cos(2*math.pi*max(0.0, t - 0.8)/4.0)
    thermo(k, 130, 250, ph)
    col = tuple(int(lerp(c, h, ph)) for c, h in zip(COLD, HOT))
    L = lerp(520, 640, ph)                     # exaggerated growth
    x0, y0 = 240, 380
    fill = tuple(int(lerp(g, c, 0.55)) for g, c in zip((150, 155, 165), col))
    k.rect((x0, y0, x0 + L, y0 + 90), fill=fill, outline=col, w=4, r=6)
    k.text((x0 + 20, y0 + 28), "STEEL BEAM", 32, (20, 24, 32), shadow=False)
    # reference line where the cold beam ends
    k.poly([(x0 + 520, y0 - 40), (x0 + 520, y0 + 140)], WHITE, 2, dash=(10, 8), a=0.6)
    if L > 528:
        k.arrow((x0 + 520, y0 + 160), (x0 + L, y0 + 160), col, 4, head=16)
    k.text((480, 640), "WARM → LONGER", 44, HOT, a=seg(t, 1.6, 2.0)*(0.4 + 0.6*ph), anchor="ma")
    k.text((480, 710), "COLD → SHORTER", 44, COLD, a=seg(t, 1.6, 2.0)*(0.4 + 0.6*(1 - ph)), anchor="ma")
    k.text((480, 800), "(growth exaggerated)", 24, GREY, a=seg(t, 1.0, 1.4), anchor="ma", bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "A 1 KM STEEL BRIDGE", GOLD, a=seg(t, 0, 0.4))
    # bridge profile
    y = 470
    k.poly([(60, y), (900, y)], WHITE, 6, prog=seg(t, 0.2, 1.4))
    for px in (60, 340, 620, 900):
        k.rect((px - 18, y + 6, px + 18, y + 230), fill=(110, 115, 125), a=seg(t, 0.6, 1.2))
    k.waves(20, 940, y + 240, amp=5, n=10, col=BLUE, w=3, t=t, a=0.6)
    k.arrow((480, y - 60), (60, y - 60), WHITE, 3, prog=seg(t, 1.2, 1.8), head=14)
    k.arrow((480, y - 60), (900, y - 60), WHITE, 3, prog=seg(t, 1.2, 1.8), head=14)
    k.text((480, y - 110), "1 KILOMETER", 38, WHITE, a=seg(t, 1.4, 1.8), anchor="ma")
    # winter vs summer
    w_ = seg(t, 2.6, 3.0); s_ = seg(t, 4.0, 4.4)
    k.text((60, 140), "WINTER NIGHT: SHORTEST", 36, COLD, a=w_, bold=False)
    k.text((60, 200), "HOT SUMMER DAY: LONGEST", 36, HOT, a=s_, bold=False)
    grow = seg(t, 4.2, 5.4)
    if grow > 0:
        k.rect((900, y - 6, 900 + 40*grow, y + 6), fill=HOT)
        k.text((880, y + 40), "UP TO", 28, GOLD, a=grow, anchor="ra", bold=False)
        k.text((880, y + 76), "≈ 0.5 M", 52, GOLD, a=grow, anchor="ra")

def joint(k, cx, cy, gap, a=1.0):
    """top view of a finger joint: the comb teeth of both deck ends interlock; gap 0 (pushed together) .. 1 (pulled apart)"""
    off = lerp(-30, 90, gap)                   # distance between the two deck edges
    CL, CR = (160, 165, 175), (118, 123, 133)
    el, er = cx - off/2 - 70, cx + off/2 + 70  # deck edges (teeth start here)
    k.rect((cx - 420, cy - 210, el, cy + 210), fill=CL, a=a)
    k.rect((er, cy - 210, cx + 420, cy + 210), fill=CR, a=a)
    for i in range(7):
        yy = cy - 210 + 30 + i*60
        if i % 2 == 0: k.rect((el - 2, yy - 22, el + 160, yy + 22), fill=CL, r=8, a=a)
        else: k.rect((er - 160, yy - 22, er + 2, yy + 22), fill=CR, r=8, a=a)

def scene2(k, t, d):
    half = d*0.55
    if t < half:
        k.tag((60, 50), "THE FINGER JOINT (FROM ABOVE)", GOLD, a=seg(t, 0, 0.4))
        gap = 0.5 - 0.5*math.cos(2*math.pi*t/3.2)
        joint(k, 480, 440, gap)
        k.text((480, 175), "SUMMER: PUSHED TOGETHER" if gap < 0.5 else "WINTER: PULLED APART", 30, HOT if gap < 0.5 else COLD, anchor="ma", bold=False, a=seg(t, 0.5, 0.9))
        k.text((480, 760), "SLIDES IN AND OUT FREELY", 38, GREEN, a=seg(t, 0.8, 1.2), anchor="ma")
    else:
        lt = t - half
        k.tag((60, 50), "WITHOUT A JOINT", RED, a=seg(lt, 0, 0.3))
        b = seg(lt, 0.3, 1.6)
        pts = [(x, 520 - 120*b*math.sin(math.pi*(x - 100)/760)) for x in range(100, 861, 20)]
        k.rect((60, 520, 100, 760), fill=(110, 115, 125)); k.rect((860, 520, 900, 760), fill=(110, 115, 125))
        k.poly(pts, WHITE if b < 0.5 else RED, 10)
        if b > 0.6:
            for cx in (300, 480, 660):
                k.poly([(cx, 520 - 120*b*math.sin(math.pi*(cx - 100)/760)), (cx + 12, 545 - 110*b*math.sin(math.pi*(cx - 100)/760)), (cx - 6, 570 - 110*b*math.sin(math.pi*(cx - 100)/760)), (cx + 8, 595 - 110*b*math.sin(math.pi*(cx - 100)/760))], RED, 4, a=seg(lt, 1.2, 1.6))
        k.text((480, 170), "IT WOULD BUCKLE", 52, RED, a=seg(lt, 1.0, 1.4), anchor="ma")
        k.text((480, 235), "OR CRACK", 52, RED, a=seg(lt, 1.4, 1.8), anchor="ma")

SCENES = [scene0, scene1, scene2]
