# Animated explanation for the solution video of Quiz #26 (spiral on the engine spinner). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

def spiral(k, c, r, ang, a=1.0):
    k.circle(c, r, fill=(15, 15, 18), outline=WHITE, w=2, a=a)
    pts = []
    for i in range(40):
        u = i/39; th = ang + u*2.4*math.pi
        pts.append((c[0] + r*0.95*u*math.cos(th), c[1] + r*0.95*u*math.sin(th)))
    k.poly(pts, WHITE, max(3, int(r*0.16)), a=a)

def engine_front(k, c, R, ang, blur, a=1.0):
    k.circle(c, R + 22, fill=(205, 208, 214), a=a)
    k.circle(c, R, fill=(28, 30, 34), a=a)
    for i in range(24):
        th = ang + i*2*math.pi/24
        k.line((c[0] + R*0.33*math.cos(th), c[1] + R*0.33*math.sin(th)), (c[0] + R*0.97*math.cos(th + 0.25), c[1] + R*0.97*math.sin(th + 0.25)),
               (150, 155, 165), 6, a=a*(1 - 0.85*blur))
    spiral(k, c, R*0.3, ang*0.6, a)

def scene0(k, t, d):
    k.tag((60, 50), "HARD TO SEE, HARD TO HEAR", RED, a=seg(t, 0, 0.4))
    blur = seg(t, 0.6, 2.0)
    engine_front(k, (480, 470), 250, t*(1 + 10*blur), blur)
    k.text((480, 130), "BLADES BLUR INTO A DISC", 34, WHITE, a=seg(t, 1.0, 1.4), anchor="ma")
    v = seg(t, d*0.5, d*0.5 + 0.4)
    k.rect((150, 770, 810, 840), fill=(0, 0, 0, 150), outline=GOLD, w=2, r=18, a=v)
    k.text((480, 787), "CREW WEAR EAR PROTECTION", 28, GOLD, a=v, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "THE SPIRAL SAYS: IT'S RUNNING", GREEN, a=seg(t, 0, 0.4))
    # top view: nacelle pointing up, danger zone in front of the intake
    zc = (480, 520)
    v = seg(t, 0.4, 1.0)
    k.arc(zc, 230, 180, 360, RED, 6, a=v)
    k.line((250, 520), (710, 520), RED, 6, a=v)
    k.text((480, 360), "DANGER ZONE", 34, RED, a=v, anchor="ma")
    k.rect((420, 520, 540, 820), fill=(205, 208, 214), outline=WHITE, w=2, r=20)
    spiral(k, (480, 560), 34, t*8)
    # a person who stays outside
    w = seg(t, 1.2, 1.8); px = lerp(820, 790, w)
    k.circle((px, 300), 18, fill=WHITE, a=w)
    k.line((px, 318), (px, 380), WHITE, 8, a=w)
    k.check((px, 440), 26, GREEN, 7, a=seg(t, 2.0, 2.4), prog=seg(t, 2.0, 2.5))
    k.text((480, 140), "SPIRAL SWIRLING = ENGINE TURNING", 32, GOLD, a=seg(t, 0.8, 1.2), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "AND THE BIRDS?", GREY, a=seg(t, 0, 0.4))
    v = seg(t, 0.3, 0.8)
    # simple bird silhouette
    c = (480, 380)
    k.poly([(c[0] - 150, c[1] - 30), (c[0] - 60, c[1] - 70), (c[0], c[1])], WHITE, 10, a=v)
    k.poly([(c[0], c[1]), (c[0] + 60, c[1] - 70), (c[0] + 150, c[1] - 30)], WHITE, 10, a=v)
    k.text((480, 150), "SCARES BIRDS AWAY?", 38, WHITE, a=v, anchor="ma")
    w = seg(t, d*0.45, d*0.45 + 0.4)
    k.rect((230, 560, 730, 650), fill=(0, 0, 0, 150), outline=GREY, w=2, r=20, a=w)
    k.text((480, 582), "NEVER PROVEN", 40, GREY, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
