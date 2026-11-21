# Animated explanation for the solution video of Quiz #20 (track ballast). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

STONE = (150, 145, 135)
CONC = (175, 172, 165)

def rock(k, c, r, seed, a=1.0, col=STONE):
    n = 6 + seed % 3
    pts = []
    for i in range(n):
        ang = 2*math.pi*i/n + 0.4*math.sin(seed*1.7 + i)
        rr = r*(0.75 + 0.25*math.sin(seed*3.1 + i*2.3))
        pts.append((c[0] + rr*math.cos(ang), c[1] + rr*math.sin(ang)))
    k.shape(pts, fill=tuple(int(v*(0.8 + 0.2*math.sin(seed))) for v in col), outline=(60, 60, 60), w=2, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "SHARP EDGES INTERLOCK", GOLD, a=seg(t, 0, 0.4))
    # left: round pebbles -> the beam slides; right: angular stones -> it stays
    push = seg(t, 1.4, 2.8)
    for side, x0 in ((0, 60), (1, 500)):
        a = seg(t, 0.2 + side*0.3, 0.7 + side*0.3)
        k.text((x0 + 200, 140), "ROUND PEBBLES" if side == 0 else "CRUSHED STONE", 32, WHITE, a=a, anchor="ma")
        # stones underneath (3 rows)
        for i in range(30):
            cx = x0 + 24 + (i % 10)*39 + (19 if (i // 10) % 2 else 0); cy = 470 + (i // 10)*40
            if side == 0: k.circle((cx, cy), 19, fill=STONE, outline=(60, 60, 60), w=2, a=a)
            else: rock(k, (cx, cy), 24, i, a=a)
        shift = 40*push if side == 0 else 3*math.sin(t*25)*push*(1 - seg(t, 2.8, 3.2))
        # stones beside the beam: they hold it (or roll away)
        for j, sx in enumerate((x0 + 40, x0 + 82, x0 + 318, x0 + 360)):
            if side == 0:
                dx = (45*push if j >= 2 else 0); dy = (55*push if j >= 2 else 0)
                k.circle((sx + dx, 410 + dy), 19, fill=STONE, outline=(60, 60, 60), w=2, a=a)
            else:
                rock(k, (sx, 412), 24, j + 40, a=a)
        k.rect((x0 + 110 + shift, 385, x0 + 290 + shift, 440), fill=CONC, outline=WHITE, w=2, r=4, a=a)
        k.text((x0 + 200 + shift, 398), "BEAM", 24, (30, 30, 35), a=a, anchor="ma", shadow=False)
        k.arrow((x0 + 10, 300), (x0 + 150, 300), RED, 6, prog=seg(t, 1.0, 1.5), head=20)
        k.text((x0 + 10, 250), "SIDEWAYS PUSH", 24, RED, a=seg(t, 1.0, 1.4), bold=False)
    k.cross((260, 690), 40, RED, 8, a=seg(t, 2.8, 3.2))
    k.text((260, 760), "SLIDES AWAY", 30, RED, a=seg(t, 2.8, 3.2), anchor="ma")
    k.check((700, 690), 40, GREEN, 8, a=seg(t, 3.1, 3.5), prog=seg(t, 3.1, 3.6))
    k.text((700, 760), "STAYS PUT", 30, GREEN, a=seg(t, 3.1, 3.5), anchor="ma")

def section(k, a=1.0):
    # cross-section: ballast trapezoid, beam, two rails
    k.shape([(120, 560), (840, 560), (920, 700), (40, 700)], fill=(120, 116, 108), a=a)
    for i in range(60):
        rock(k, (70 + (i*53) % 820, 575 + ((i*29) % 110)), 14, i, a=a*0.9)
    k.rect((180, 520, 780, 565), fill=CONC, outline=WHITE, w=2, r=4, a=a)
    for x in (300, 660):
        k.shape([(x - 26, 520), (x + 26, 520), (x + 8, 505), (x + 8, 470), (x + 18, 465), (x + 18, 450), (x - 18, 450), (x - 18, 465), (x - 8, 470), (x - 8, 505)], fill=(140, 140, 145), a=a)
    k.rect((0, 700, 960, 860), fill=(70, 55, 40), a=a)
    k.text((60, 820), "GROUND", 26, (200, 180, 150), a=a, bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "SPREADS THE WEIGHT", GOLD, a=seg(t, 0, 0.4))
    section(k, a=seg(t, 0.1, 0.6))
    # train wheel load arrows on the rails
    for x in (300, 660):
        k.arrow((x, 250), (x, 440), RED, 8, prog=seg(t, 0.6, 1.2), head=26)
    k.text((480, 200), "HUGE WEIGHT ON TWO THIN RAILS", 32, RED, a=seg(t, 0.6, 1.0), anchor="ma")
    # pressure fanning out through the stones
    f = seg(t, 1.4, 2.6)
    for x in (300, 660):
        for dx in (-1, -0.5, 0, 0.5, 1):
            k.arrow((x, 570), (x + dx*170*f, 570 + 230*f), GOLD, 4, prog=f, head=14, a=0.9)
    k.text((480, 150), "…SPREAD OVER A WIDE AREA", 32, GOLD, a=seg(t, 2.4, 2.8), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "WATER DRAINS AWAY", GOLD, a=seg(t, 0, 0.4))
    section(k)
    # rain falling through the gaps
    for i in range(46):
        x = 60 + (i*97) % 860
        ph = ((t*0.9 + i*0.173) % 1.0)
        y = lerp(120, 760, ph)
        k.line((x, y), (x - 4, y + 22), BLUE, 3, a=0.85*seg(t, 0.2, 0.6))
    k.text((480, 150), "RAIN RUNS STRAIGHT THROUGH THE GAPS", 30, BLUE, a=seg(t, 0.6, 1.0), anchor="ma")
    k.text((480, 760), "GROUND STAYS FIRM", 36, GREEN, a=seg(t, d*0.45, d*0.45 + 0.4), anchor="ma")

SCENES = [scene0, scene1, scene2]
