# Animated explanation for the solution video of Quiz #17 (aerial marker balls). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

ORANGE = (255, 130, 40); BALLW = (235, 235, 235); YEL = (250, 215, 60); HILL = (60, 72, 66)
BALLS = (ORANGE, BALLW, YEL)

def cable_y(x, x0=140, x1=820, y0=260, sag=150):
    u = (x - x0)/(x1 - x0); return y0 + sag*4*u*(1 - u)

def valley(k, a=1.0, cable_a=1.0):
    k.shape([(0, 880), (0, 320), (90, 280), (190, 300), (330, 640), (480, 760), (630, 640), (760, 310), (860, 270), (960, 300), (960, 880)], fill=HILL, a=a)
    k.shape([(380, 760), (580, 760), (530, 790), (430, 790)], fill=(70, 110, 140), a=a)
    for x in (140, 820):
        k.line((x, 330), (x, 250), GREY, 6, a=a); k.line((x - 30, 262), (x + 30, 262), GREY, 4, a=a)
    pts = [(x, cable_y(x)) for x in range(140, 821, 20)]
    k.poly(pts, GREY, 2, a=a*cable_a)

def heli(k, x, y, a, t):
    k.rect((x - 46, y - 18, x + 30, y + 16), fill=(30, 34, 40), outline=WHITE, w=2, r=14, a=a)
    k.line((x + 30, y - 4), (x + 104, y - 12), WHITE, 5, a=a)
    span = 70*abs(math.cos(t*20))
    k.line((x - 8 - span, y - 30), (x - 8 + span, y - 30), WHITE, 3, a=a)
    k.line((x - 8, y - 18), (x - 8, y - 30), WHITE, 3, a=a)
    k.line((x - 40, y + 26), (x + 24, y + 26), WHITE, 3, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "SEEN FROM THE AIR", GOLD, a=seg(t, 0, 0.4))
    valley(k, a=seg(t, 0.1, 0.6), cable_a=0.35)
    v = seg(t, 1.0, 1.5)
    k.circle((480, cable_y(480)), 70, outline=GOLD, w=3, a=v)
    k.text((480, 150), "A THIN CABLE", 40, WHITE, a=v, anchor="ma")
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((480, 200), "ALMOST INVISIBLE", 40, RED, a=w, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "MARKER BALLS", GREEN, a=seg(t, 0, 0.4))
    valley(k, cable_a=0.5)
    hx = lerp(1000, 600, seg(t, 0.2, d*0.5)); hy = 470
    heli(k, hx, hy, 1.0, t)
    xs = (300, 480, 660)
    for j, x in enumerate(xs):
        w = seg(t, d*0.45 + j*0.25, d*0.45 + j*0.25 + 0.3)
        k.circle((x, cable_y(x)), 20*w, fill=BALLS[j], outline=(0, 0, 0), w=1)
    v = seg(t, d*0.7, d*0.7 + 0.4)
    k.text((480, 150), "EASY TO SPOT FROM FAR AWAY", 36, GREEN, a=v, anchor="ma")
    k.check((480, 220), 26, GREEN, 7, a=v, prog=v)

def scene2(k, t, d):
    k.tag((60, 50), "FAA RECOMMENDATION (USA)", BLUE, a=seg(t, 0, 0.4))
    y = 380
    k.line((60, y), (900, y), GREY, 3, a=seg(t, 0.1, 0.5))
    for j in range(5):
        x = 120 + j*180
        w = seg(t, 0.4 + j*0.3, 0.7 + j*0.3)
        k.circle((x, y), 34*w, fill=BALLS[j % 3], outline=(0, 0, 0), w=1)
    v = seg(t, 2.0, 2.5)
    k.line((120, 470), (300, 470), GOLD, 3, a=v); k.line((120, 450), (120, 490), GOLD, 3, a=v); k.line((300, 450), (300, 490), GOLD, 3, a=v)
    k.text((210, 500), "~200 FT", 34, GOLD, a=v, anchor="ma")
    k.text((210, 545), "(~60 m)", 24, GREY, a=v, anchor="ma", bold=False)
    w = seg(t, 2.8, 3.2)
    k.text((640, 470), "ORANGE · WHITE · YELLOW", 30, WHITE, a=w, anchor="ma")
    k.text((640, 510), "TAKING TURNS", 26, GREY, a=w, anchor="ma", bold=False)
    for j, lab in enumerate(("CANYONS", "LAKES", "RIVERS")):
        z = seg(t, d*0.35 + j*0.3, d*0.35 + j*0.3 + 0.3)
        k.tag((110 + j*260, 650), lab, BLUE, a=z, size=30)

SCENES = [scene0, scene1, scene2]
