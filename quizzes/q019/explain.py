# Animated explanation for the solution video of Quiz #19 (runaway truck ramp). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HOT, COLD = (255, 110, 60), (150, 160, 175)
GRAVEL = (150, 135, 115)

def truck(k, x, y, ang, a=1.0, sink=0.0):
    """tiny side-view truck, x,y = rear wheel contact point, ang = slope angle (rad, + = nose down)"""
    ca, sa = math.cos(ang), math.sin(ang)
    def P(u, v): return (x + u*ca + v*sa, y + u*sa - v*ca + sink)
    k.shape([P(-10, 18), P(150, 18), P(150, 78), P(-10, 78)], fill=(225, 225, 220), a=a)       # trailer
    k.shape([P(158, 18), P(215, 18), P(215, 70), P(188, 70), P(182, 82), P(158, 82)], fill=(170, 30, 25), a=a)  # cab
    for u in (10, 40, 175, 205):
        k.circle(P(u, 12), 12, fill=(20, 20, 22), outline=(120, 120, 120), w=2, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "LONG, STEEP DOWNHILL", GOLD, a=seg(t, 0, 0.4))
    # the slope
    x0, y0, x1, y1 = 60, 300, 900, 620
    ang = math.atan2(y1 - y0, x1 - x0)
    k.shape([(x0, y0), (x1, y1), (x1, 760), (x0, 760)], fill=(60, 64, 70), a=seg(t, 0.1, 0.6))
    k.line((x0, y0), (x1, y1), WHITE, 4, prog=seg(t, 0.1, 0.8))
    u = seg(t, 0.4, d - 0.2)*0.62
    tx, ty = lerp(x0, x1, u), lerp(y0, y1, u)
    truck(k, tx, ty, ang, a=seg(t, 0.3, 0.7))
    # brake temperature gauge
    heat = seg(t, 0.8, d - 0.6)
    col = tuple(int(lerp(c, h, heat)) for c, h in zip(COLD, HOT))
    k.text((640, 130), "BRAKE TEMPERATURE", 26, WHITE, a=seg(t, 0.6, 1.0), bold=False)
    k.rect((640, 170, 900, 210), fill=(0, 0, 0, 150), outline=WHITE, w=2, r=10, a=seg(t, 0.6, 1.0))
    k.rect((646, 176, 646 + max(2, 248*heat), 204), fill=col, r=8, a=seg(t, 0.6, 1.0))
    # glowing brake on the truck's wheels
    if heat > 0.2:
        for uu in (10, 40):
            ca, sa = math.cos(ang), math.sin(ang)
            k.circle((tx + uu*ca + 12*sa, ty + uu*sa - 12*ca), 8, fill=col, a=heat)
    k.text((480, 790), "ENERGY → HEAT → BRAKES FADE", 36, HOT, a=seg(t, d*0.6, d*0.6 + 0.4), anchor="ma")

def scene1(k, t, d):
    k.clip(0.30 + 0.25*min(1, t/max(d, 0.1)), box=(0, 0, 960, 880), dim=0.2)
    k.tag((60, 50), "RUNAWAY TRUCK RAMP", GOLD, a=seg(t, 0, 0.4))
    a = seg(t, 0.8, 1.3)
    k.rect((150, 690, 810, 810), fill=(0, 0, 0, 170), r=24, a=a)
    k.text((480, 712), "DEEP, LOOSE, ROUNDED GRAVEL", 40, WHITE, a=a, anchor="ma")
    k.text((480, 762), "an escape lane off the highway", 28, GREY, a=seg(t, 1.4, 1.8), anchor="ma", bold=False)

def scene2(k, t, d):
    k.tag((60, 50), "HOW THE GRAVEL STOPS IT", GOLD, a=seg(t, 0, 0.4))
    gy = 520
    k.rect((40, gy, 920, 760), fill=GRAVEL, a=seg(t, 0.1, 0.5))
    for i in range(140):
        gx = 50 + (i*67) % 860; gyy = gy + 12 + ((i*37) % 220)
        k.circle((gx, gyy), 9 + (i % 3)*3, fill=(120 + (i % 4)*15, 108 + (i % 4)*12, 92 + (i % 4)*10), a=seg(t, 0.1, 0.5))
    # wheel rolls in and sinks
    u = seg(t, 0.4, d*0.55)
    wx = lerp(140, 560, 1 - (1 - u)**2)
    sink = 70*u
    k.circle((wx, gy - 70 + sink), 70, fill=(25, 25, 28), outline=(140, 140, 140), w=4)
    k.circle((wx, gy - 70 + sink), 30, fill=(170, 170, 175))
    # pile pushed up in front of the wheel + drag arrow
    pa = u
    k.shape([(wx + 40, gy), (wx + 110, gy - 30*pa), (wx + 170, gy)], fill=GRAVEL, a=pa)
    k.arrow((wx + 40, gy - 150), (wx - 140, gy - 150), RED, 6, prog=seg(t, 1.0, 1.6), head=24)
    k.text((wx - 50, gy - 215), "DRAG", 34, RED, a=seg(t, 1.2, 1.6), anchor="ma")
    # speed bar
    v = 1 - seg(t, 0.6, d*0.75)
    k.text((60, 130), "SPEED", 26, WHITE, a=seg(t, 0.3, 0.7), bold=False)
    k.rect((60, 170, 460, 205), fill=(0, 0, 0, 150), outline=WHITE, w=2, r=10, a=seg(t, 0.3, 0.7))
    k.rect((66, 176, 66 + max(2, 388*v), 199), fill=GREEN if v < 0.05 else GOLD, r=8, a=seg(t, 0.3, 0.7))
    k.check((560, 190), 34, GREEN, 8, a=seg(t, d*0.78, d*0.78 + 0.3), prog=seg(t, d*0.78, d*0.78 + 0.5))
    k.text((480, 800), "TOWED OUT LATER — NO CRASH", 34, GREEN, a=seg(t, d*0.8, d*0.8 + 0.4), anchor="ma")

SCENES = [scene0, scene1, scene2]
