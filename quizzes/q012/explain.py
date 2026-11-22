# Animated explanation for the solution video of Quiz #12 (static wicks). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

BODY = (205, 210, 218)

def plane(k, cx, cy, s=1.0, a=1.0):
    """simple side view of an airliner"""
    pts = [(-300, 0), (-270, -28), (200, -34), (260, -26), (300, -6), (300, 10), (240, 26), (-250, 26), (-300, 10)]
    k.shape([(cx + x*s, cy + y*s) for x, y in pts], fill=BODY, outline=WHITE, w=2, a=a)
    k.shape([(cx + x*s, cy + y*s) for x, y in [(-200, -30), (-290, -130), (-250, -130), (-140, -30)]], fill=BODY, outline=WHITE, w=2, a=a)
    k.shape([(cx + x*s, cy + y*s) for x, y in [(-40, 10), (-120, 70), (-60, 70), (60, 10)]], fill=(180, 186, 196), outline=WHITE, w=2, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "FRICTION = STATIC CHARGE", GOLD, a=seg(t, 0, 0.4))
    a = seg(t, 0.1, 0.6)
    plane(k, 520, 450, 1.1, a)
    # rain / snow streaks hitting the plane
    for i in range(40):
        ph = (t*1.3 + i*0.137) % 1.0
        x = lerp(950, 100, ph) + (i*53) % 120; y = 160 + (i*71) % 560
        k.line((x, y), (x + 26, y - 6), BLUE, 3, a=0.8*seg(t, 0.3, 0.8))
    # plus signs building up on the skin
    n = int(22*seg(t, 0.8, d - 0.6))
    for j in range(n):
        x = 240 + (j*97) % 560; y = 400 + ((j*37) % 3)*45 - (40 if x < 300 else 0)
        k.text((x, y), "+", 40, GOLD, anchor="mm", shadow=False)
    k.text((480, 760), "THE PLANE CHARGES UP", 36, GOLD, a=seg(t, 1.6, 2.0), anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "UNCONTROLLED DISCHARGE", RED, a=seg(t, 0, 0.4))
    plane(k, 480, 380, 1.0)
    for j in range(16):
        x = 220 + (j*97) % 520; y = 370 + ((j*37) % 3)*30
        k.text((x, y), "+", 36, GOLD, anchor="mm", shadow=False)
    # crackling sparks off the wing edge, pulsing
    for i in range(4):
        on = (math.sin(t*14 + i*1.9) > 0.3) * seg(t, 0.4, 0.8)
        if on:
            x0, y0 = 200 + i*150, 420
            pts = [(x0, y0)]
            for s in range(5): pts.append((x0 + 18*((-1)**s), y0 + 22*(s + 1)))
            k.poly(pts, (255, 240, 160), 4)
    # radio with noise
    k.rect((300, 600, 660, 760), fill=(30, 34, 44), outline=WHITE, w=2, r=14, a=seg(t, 0.8, 1.2))
    k.text((480, 615), "RADIO / NAV", 24, GREY, a=seg(t, 0.8, 1.2), anchor="ma", bold=False)
    pts = [(320 + i*8, 700 + (math.sin(i*2.7 + t*30)*30 if (i + int(t*12)) % 7 < 4 else 0)) for i in range(41)]
    k.poly(pts, RED, 3, a=seg(t, 1.0, 1.4))
    k.cross((710, 680), 30, RED, 7, a=seg(t, 1.8, 2.2))

def scene2(k, t, d):
    k.tag((60, 50), "QUIET LEAK THROUGH SHARP TIPS", GREEN, a=seg(t, 0, 0.4))
    # close-up of a wing trailing edge with three wicks
    k.shape([(60, 260), (900, 260), (900, 330), (60, 360)], fill=BODY, outline=WHITE, w=2)
    k.text((80, 200), "TRAILING EDGE", 24, GREY, bold=False)
    tips = []
    for i, x in enumerate((240, 480, 720)):
        k.line((x, 330 - (x - 60)*30/840 + 10), (x + 40, 520), (30, 30, 34), 12)
        k.circle((x + 40, 520), 7, fill=GOLD)
        tips.append((x + 40, 520))
    # charges flowing along the wicks and fading into the air
    f = seg(t, 0.5, 1.0)
    for i, (x, y) in enumerate(tips):
        for j in range(6):
            ph = (t*0.8 + j/6 + i*0.21) % 1.0
            px = x + ph*60*math.cos(j); py = y + 30 + ph*160
            k.text((px, py), "+", 30, GOLD, a=f*(1 - ph), anchor="mm", shadow=False)
    k.check((260, 760), 34, GREEN, 8, a=seg(t, 1.5, 1.9), prog=seg(t, 1.5, 2.0))
    k.text((310, 740), "RADIOS STAY CLEAR", 32, GREEN, a=seg(t, 1.5, 1.9))
    k.tag((520, 120), "NOT LIGHTNING RODS", RED, a=seg(t, d*0.55, d*0.55 + 0.4))

SCENES = [scene0, scene1, scene2]
