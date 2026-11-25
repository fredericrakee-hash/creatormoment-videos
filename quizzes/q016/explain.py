# Animated explanation for the solution video of Quiz #16 (windshield frit band). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

GLASS = (120, 170, 200); BODY = (70, 74, 84); GLUE = (225, 215, 170); UV = (190, 120, 255); FRIT = (18, 18, 20)

def section(k, a=1.0, frit=0.0):
    # cross-section: windshield on top, glue bead, car body flange below
    k.rect((80, 330, 880, 370), fill=GLASS + (150,), outline=WHITE, w=2, a=a)
    k.text((860, 285), "GLASS", 24, GLASS, a=a, anchor="ra", bold=False)
    k.rect((300, 370, 480, 430), fill=GLUE, r=18, a=a)
    k.line((330, 425), (300, 560), GLUE, 2, a=a)
    k.text((300, 570), "URETHANE GLUE", 26, GLUE, a=a, anchor="ma", bold=False)
    k.shape([(80, 430), (700, 430), (760, 520), (760, 640), (720, 640), (720, 530), (680, 470), (80, 470)], fill=BODY, outline=GREY, w=2, a=a)
    k.text((120, 500), "CAR BODY", 24, GREY, a=a, bold=False)
    if frit > 0:
        k.rect((80, 352, 80 + 480*frit, 372), fill=FRIT, outline=GOLD, w=2, a=frit)

def sun(k, a):
    k.circle((150, 200), 40, fill=GOLD, a=a)
    for j in range(8):
        ang = j*math.pi/4
        k.line((150 + 54*math.cos(ang), 200 + 54*math.sin(ang)), (150 + 72*math.cos(ang), 200 + 72*math.sin(ang)), GOLD, 4, a=a)

def rays(k, t, a, stop_y):
    for j in range(3):
        x0, y0 = 230 + j*40, 200 + j*8
        x1, y1 = 330 + j*45, stop_y
        ph = (t*0.9 + j*0.3) % 1.0
        k.arrow((x0, y0), (x1, y1), UV, 4, prog=0.3 + 0.7*ph, a=a, head=16)

def scene0(k, t, d):
    k.tag((60, 50), "CROSS-SECTION: WINDSHIELD EDGE", GOLD, a=seg(t, 0, 0.4))
    section(k, a=seg(t, 0.2, 0.7))
    sun(k, seg(t, 0.8, 1.2))
    v = seg(t, 1.2, 1.6)
    rays(k, t, v, 395)
    k.text((560, 170), "UV LIGHT", 36, UV, a=v)
    w = seg(t, d*0.6, d*0.6 + 0.5)
    for j in range(4):
        x = 320 + j*42
        k.poly([(x, 375), (x + 10, 395), (x - 4, 410), (x + 8, 428)], RED, 3, a=w)
    k.text((480, 720), "GLUE BREAKS DOWN", 44, RED, a=w, anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "THE BLACK FRIT BAND", GREEN, a=seg(t, 0, 0.4))
    f = seg(t, 0.3, 1.2)
    section(k, frit=f)
    sun(k, 1.0)
    rays(k, t, 1.0, 326)
    k.text((580, 380), "FRIT (BLACK CERAMIC)", 26, GOLD, a=f, anchor="la")
    items = (("BLOCKS THE UV", 1.4), ("HIDES THE GLUE", 2.4), ("ROUGH SURFACE TO GRIP", 3.4))
    for j, (lab, t0) in enumerate(items):
        w = seg(t, t0, t0 + 0.4)
        k.check((110, 712 + j*58), 16, GREEN, 5, a=w, prog=w)
        k.text((145, 696 + j*58), lab, 32, WHITE, a=w)

def scene2(k, t, d):
    k.tag((60, 50), "WHY THE DOTS SHRINK", BLUE, a=seg(t, 0, 0.4))
    # solid band on the left, then dots shrinking towards the clear glass
    k.rect((60, 200, 900, 560), fill=GLASS + (60,), outline=WHITE, w=2, r=10, a=seg(t, 0.1, 0.5))
    k.rect((60, 200, 220, 560), fill=FRIT, a=seg(t, 0.3, 0.7))
    cols = 9
    for c in range(cols):
        r = 22*(1 - c/cols)
        if r < 2: continue
        x = 250 + c*60
        w = seg(t, 0.6 + c*0.12, 0.9 + c*0.12)
        for row in range(6):
            y = 230 + row*60 + (30 if c % 2 else 0)
            if y > 540: continue
            k.circle((x, y), r*w, fill=FRIT, a=1.0)
    v = seg(t, d*0.3, d*0.3 + 0.4)
    k.arrow((250, 610), (760, 610), GOLD, 4, prog=v)
    k.text((480, 640), "SMOOTH FADE INTO CLEAR GLASS", 30, GOLD, a=v, anchor="ma")
    w = seg(t, d*0.6, d*0.6 + 0.4)
    k.text((480, 730), "EVEN HEAT WHEN THE GLASS IS BENT", 32, WHITE, a=w, anchor="ma")

SCENES = [scene0, scene1, scene2]
