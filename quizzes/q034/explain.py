# Animated explanation for the solution video of Quiz #34 (Curiosity's Morse-code wheel tracks). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

SAND = (120, 62, 32); TRACK = (80, 40, 22); MARK = (235, 170, 110)
CODE = [("J", ".---"), ("P", ".--."), ("L", ".-..")]

def morse_row(k, x0, y, a=1.0, prog=1.0, labels=True, h=34, sc=1.0):
    x = x0; n = sum(len(c) for _, c in CODE); i = 0
    for L, c in CODE:
        xs = x
        for ch in c:
            w = (20 if ch == "." else 60)*sc
            if i/n < prog: k.rect((x, y - h/2, x + w, y + h/2), fill=MARK, r=4, a=a)
            x += w + 12*sc; i += 1
        if labels: k.text(((xs + x - 12*sc)/2, y + h/2 + 16), L, 40, GOLD, a=a*seg(prog, 0.3, 0.6), anchor="ma")
        x += 40*sc
    return x

def scene0(k, t, d):
    k.tag((60, 50), "HIDDEN IN THE TRACKS", GOLD, a=seg(t, 0, 0.4))
    k.rect((40, 250, 920, 470), fill=TRACK, outline=GREY, w=2, r=10, a=seg(t, 0.2, 0.6))
    for j in range(16):
        x = 70 + j*56
        k.line((x, 260), (x + 20, 360 - 60), (60, 30, 15), 6, a=seg(t, 0.2, 0.6))
        k.line((x, 460), (x + 20, 420), (60, 30, 15), 6, a=seg(t, 0.2, 0.6))
    morse_row(k, 90, 360, prog=seg(t, 0.8, 2.6))
    v = seg(t, d*0.55, d*0.55 + 0.5)
    k.text((480, 600), "J · P · L", 64, WHITE, a=v, anchor="ma")
    k.text((480, 690), "JET PROPULSION LABORATORY", 30, GOLD, a=v, anchor="ma")
    k.text((480, 740), "the NASA lab that built the rover", 26, GREY, a=v, anchor="ma", bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "THE PROBLEM", RED, a=seg(t, 0, 0.4))
    k.rect((40, 520, 920, 600), fill=SAND, a=seg(t, 0.2, 0.5))
    ang = t*5.0
    cx = lerp(260, 420, seg(t, 0.6, d))
    k.circle((cx, 450), 70, fill=(150, 150, 155), outline=WHITE, w=3, a=seg(t, 0.2, 0.5))
    for j in range(6):
        a_ = ang + j*math.pi/3
        k.line((cx, 450), (cx + 60*math.cos(a_), 450 + 60*math.sin(a_)), (60, 60, 66), 5, a=seg(t, 0.2, 0.5))
    k.arrow((300, 330), (840, 330), GREY, 4, prog=seg(t, 0.6, 1.4))
    k.text((570, 280), "HOW FAR THE WHEELS TURNED", 30, GREY, a=seg(t, 0.8, 1.2), anchor="ma")
    k.arrow((300, 680), (480, 680), GOLD, 5, prog=seg(t, 1.6, 2.4))
    k.text((400, 710), "HOW FAR IT REALLY MOVED", 30, GOLD, a=seg(t, 2.0, 2.4), anchor="ma")
    k.text((480, 790), "LOOSE SAND = SLIP", 32, RED, a=seg(t, d*0.6, d*0.6 + 0.4), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "VISUAL ODOMETRY", GREEN, a=seg(t, 0, 0.4))
    k.rect((40, 380, 920, 520), fill=TRACK, r=10, a=seg(t, 0.2, 0.5))
    morse_row(k, 75, 450, a=seg(t, 0.2, 0.5), labels=False, h=26, sc=0.4)
    morse_row(k, 555, 450, a=seg(t, 0.2, 0.5), labels=False, h=26, sc=0.4)
    for j, (x0, x1) in enumerate(((60, 380), (540, 860))):
        k.poly([(x0, 360), (x1, 360), (x1, 540), (x0, 540)], GOLD, 3, closed=True, a=seg(t, 0.8 + j*0.6, 1.2 + j*0.6), dash=(14, 10))
    k.text((220, 320), "PHOTO 1", 26, GOLD, a=seg(t, 0.9, 1.2), anchor="ma")
    k.text((700, 320), "PHOTO 2", 26, GOLD, a=seg(t, 1.5, 1.8), anchor="ma")
    k.arrow((220, 600), (700, 600), GREEN, 5, prog=seg(t, 2.0, 2.8))
    k.text((460, 640), "TRUE DISTANCE", 34, GREEN, a=seg(t, 2.4, 2.8), anchor="ma")
    k.check((480, 780), 34, GREEN, 7, a=seg(t, d*0.7, d*0.7 + 0.3), prog=seg(t, d*0.7, d*0.7 + 0.6))

SCENES = [scene0, scene1, scene2]
