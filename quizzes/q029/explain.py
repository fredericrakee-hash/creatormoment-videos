# Animated explanation for the solution video of Quiz #29 (Soyuz soft-landing engines). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

CHAR = (70, 52, 40); GROUND = (90, 72, 44); FIRE = (255, 190, 90)

def capsule(k, x, y, s=1.0, a=1.0, shield=True):
    pts = [(x - 60*s, y), (x - 64*s, y - 30*s), (x - 52*s, y - 80*s), (x - 26*s, y - 112*s), (x, y - 118*s),
           (x + 26*s, y - 112*s), (x + 52*s, y - 80*s), (x + 64*s, y - 30*s), (x + 60*s, y)]
    k.shape(pts, fill=CHAR, outline=WHITE, w=2, a=a)
    if shield:
        k.shape([(x - 60*s, y), (x + 60*s, y), (x + 40*s, y + 12*s), (x - 40*s, y + 12*s)], fill=(120, 110, 100), outline=WHITE, w=2, a=a)

def ground(k, y=760, a=1.0):
    k.rect((0, y, 960, 880), fill=GROUND, a=a)
    k.line((0, y), (960, y), GREY, 2, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "UNDER THE MAIN PARACHUTE", GOLD, a=seg(t, 0, 0.4))
    ground(k)
    p = seg(t, 0.2, d*0.9)
    cy = lerp(300, 700, p)
    k.line((480, cy - 118), (480, 120), GREY, 2, a=0.8)
    capsule(k, 480, cy)
    v = seg(t, 0.8, 1.2)
    k.arrow((640, 260), (640, 420), GOLD, 5, prog=v, a=v)
    k.text((660, 300), "7 m/s", 48, GOLD, a=v)
    k.text((660, 360), "≈ 25 km/h", 30, GREY, a=v, bold=False)
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((480, 820), "TOO HARD A JOLT FOR THE CREW", 32, RED, a=w, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "UNDER THE CAPSULE", BLUE, a=seg(t, 0, 0.4))
    capsule(k, 480, 420, s=2.0, shield=False)
    p = seg(t, 0.3, 1.6)
    k.shape([(360, 420 + 380*p), (600, 420 + 380*p), (560, 444 + 380*p), (400, 444 + 380*p)], fill=(120, 110, 100), outline=WHITE, w=2, a=1 - seg(t, 1.4, 1.8))
    k.text((480, 760), "HEAT SHIELD DROPPED", 28, GREY, a=seg(t, 0.6, 1.0)*(1 - seg(t, 1.8, 2.2)), anchor="ma")
    for j in range(6):
        x = 480 + (j - 2.5)*36
        z = seg(t, 1.6 + j*0.15, 1.9 + j*0.15)
        k.rect((x - 12, 420, x + 12, 446), fill=(40, 40, 44), outline=GOLD, w=2, a=z)
    v = seg(t, 2.6, 3.0)
    k.text((480, 520), "6 SMALL SOLID-FUEL ENGINES", 34, GOLD, a=v, anchor="ma")
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.line((480, 460), (480, 740), BLUE, 3, a=w, prog=w)
    ground(k, 760, a=w)
    k.text((500, 610), "GAMMA-RAY ALTIMETER", 26, BLUE, a=w)
    k.text((500, 645), "MEASURES THE HEIGHT", 22, GREY, a=w, bold=False)

def scene2(k, t, d):
    k.tag((60, 50), "SOFT LANDING", GREEN, a=seg(t, 0, 0.4))
    ground(k, 700)
    p = seg(t, 0.2, 1.6)
    cy = lerp(420, 612, p) + 76*seg(t, 2.2, 3.6)
    capsule(k, 480, cy, s=1.4)
    f = seg(t, 1.6, 1.75)*(1 - seg(t, 2.6, 3.0))
    for j in range(6):
        x = 480 + (j - 2.5)*22
        k.line((x, cy + 18), (x + (j - 2.5)*4, cy + 18 + 70*f), FIRE, 8, a=f)
    k.circle((480, 690), 60 + 120*f, fill=FIRE, a=0.25*f)
    v = seg(t, 1.6, 2.0)
    k.text((760, 560), "~1 m", 44, GOLD, a=v*(1 - seg(t, 3.0, 3.3)), anchor="ma")
    k.text((200, 220), "7 m/s", 46, RED, a=seg(t, 0.4, 0.8), anchor="ma")
    k.arrow((300, 245), (560, 245), GREY, 3, prog=seg(t, 2.4, 3.0), a=seg(t, 2.4, 3.0))
    k.text((720, 220), "1.5 m/s", 46, GREEN, a=seg(t, 3.0, 3.4), anchor="ma")
    k.check((480, 160), 26, GREEN, 7, a=seg(t, d*0.75, d*0.75 + 0.3), prog=seg(t, d*0.75, d*0.75 + 0.3))

SCENES = [scene0, scene1, scene2]
