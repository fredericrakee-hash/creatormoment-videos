# Animated explanation for the solution video of Quiz #21 (load line / Plimsoll mark). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HULL = (22, 36, 58); SEA = (20, 70, 100); PAINT = (236, 234, 226)

def mark(k, cx, cy, s=1.0, a=1.0, labels=True):
    """load line mark: circle + bar at (cx, cy) = summer line, ladder to the right. 1 unit = s px per mm/2"""
    r = 60*s
    k.circle((cx, cy), r, outline=PAINT, w=7*s, a=a)
    k.rect((cx - 92*s, cy - 7*s, cx + 92*s, cy), fill=PAINT, a=a)
    vx = cx + 215*s
    k.rect((vx - 4*s, cy - 205*s, vx + 4*s, cy + 135*s), fill=PAINT, a=a)
    for dz, lab, side in ((100, "T", 1), (0, "S", 1), (-100, "W", 1), (-125, "WNA", 1), (100, "F", -1), (200, "TF", -1)):
        y = cy - dz*s
        x0, x1 = (vx, vx + 90*s) if side > 0 else (vx - 90*s, vx)
        k.rect((x0, y - 7*s, x1, y), fill=PAINT, a=a)
        if labels:
            if side > 0: k.text((x1 + 10*s, y - 4*s), lab, int(26*s), PAINT, a=a, anchor="lm", shadow=False)
            else: k.text((x0 - 10*s, y - 4*s), lab, int(26*s), PAINT, a=a, anchor="rm", shadow=False)

def water(k, y, x0=0, x1=960, a=1.0, t=0.0, col=SEA):
    pts = [(x, y + 5*math.sin(x/40 + t*2)) for x in range(int(x0), int(x1) + 1, 12)]
    k.shape(pts + [(x1, 880), (x0, 880)], fill=col + (200,), a=a)
    k.poly(pts, BLUE, 3, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "THE LEGAL LOADING LIMIT", GOLD, a=seg(t, 0, 0.4))
    k.rect((60, 140, 900, 880), fill=HULL, a=seg(t, 0.1, 0.5))
    mark(k, 330, 470, 1.2, a=seg(t, 0.3, 0.8))
    # water rises as the ship is loaded, stops exactly at the S line
    wl = lerp(820, 470, seg(t, 1.0, d*0.75))
    water(k, wl, 60, 900, a=seg(t, 0.6, 1.0), t=t)
    k.text((480, 820), "MORE CARGO  →  SHIP SINKS", 30, WHITE, a=seg(t, 1.0, 1.4), anchor="ma")
    done = seg(t, d*0.75, d*0.75 + 0.4)
    k.arrow((870, 380), (690, 466), GREEN, 5, prog=done, head=20)
    k.text((880, 330), "STOP HERE", 30, GREEN, a=done, anchor="ra")
    k.cross((800, 260), 26, RED, 6, a=done)
    k.text((760, 260), "NEVER ABOVE", 24, RED, a=done, anchor="rm", bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "FRESH WATER = LESS LIFT", BLUE, a=seg(t, 0, 0.4))
    for j, (x0, lab, dens, wl) in enumerate(((70, "SEA", "1,025 kg/m³", 470), (510, "RIVER", "1,000 kg/m³", 440))):
        a = seg(t, 0.2 + j*0.6, 0.7 + j*0.6)
        sink = 0 if j == 0 else 30*seg(t, 1.6, 2.6)
        # little ship hull
        k.shape([(x0 + 20, 330 + sink), (x0 + 360, 330 + sink), (x0 + 330, 520 + sink), (x0 + 50, 520 + sink)], fill=(60, 70, 90), outline=WHITE, w=2, a=a)
        k.rect((x0 + 120, 250 + sink, x0 + 260, 330 + sink), fill=(200, 200, 205), a=a)
        water(k, 470, x0, x0 + 380, a=a, t=t, col=(20, 70, 100) if j == 0 else (40, 90, 80))
        k.text((x0 + 190, 600), lab, 36, WHITE, a=a, anchor="ma")
        k.text((x0 + 190, 650), dens, 28, GREY, a=a, anchor="ma", bold=False)
    k.text((700, 180), "FLOATS DEEPER", 30, GOLD, a=seg(t, 2.4, 2.8), anchor="ma")
    k.arrow((880, 200), (880, 300), GOLD, 5, prog=seg(t, 2.4, 2.9), head=18)
    # mini ladder with the extra lines highlighted
    m = seg(t, d*0.5, d*0.5 + 0.5)
    k.rect((260, 700, 700, 860), fill=HULL, r=14, a=m)
    mark(k, 380, 800, 0.42, a=m, labels=False)
    k.text((560, 720), "F / TF: FRESH WATER", 24, BLUE, a=m, bold=False)
    k.text((560, 790), "W / WNA: WINTER SEAS", 24, GOLD, a=m*seg(t, d*0.65, d*0.65 + 0.4), bold=False)

def scene2(k, t, d):
    k.tag((60, 50), "WHY IT EXISTS", GOLD, a=seg(t, 0, 0.4))
    # overloaded ship sinking
    a = seg(t, 0.2, 0.6); s = seg(t, 0.8, 2.6)
    ang = -12*s
    cx, cy = 260, 380 + 120*s
    pts = [(-170, -40), (170, -40), (140, 50), (-140, 50)]
    def rot(p):
        c, si = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        return (cx + p[0]*c - p[1]*si, cy + p[0]*si + p[1]*c)
    k.shape([rot(p) for p in pts], fill=(70, 70, 80), outline=WHITE, w=2, a=a)
    for i in range(5):
        for j in range(3):
            q = [rot((-150 + i*60, -40 - j*34)), rot((-94 + i*60, -40 - j*34)), rot((-94 + i*60, -72 - j*34)), rot((-150 + i*60, -72 - j*34))]
            k.shape(q, fill=(150, 70, 50), outline=(40, 40, 40), w=1, a=a)
    water(k, 420, 40, 480, a=a, t=t)
    k.text((260, 160), "1800s: OVERLOADED", 30, RED, a=seg(t, 0.4, 0.8), anchor="ma")
    k.cross((260, 700), 34, RED, 8, a=seg(t, 2.2, 2.6))
    # the law
    b = seg(t, d*0.45, d*0.45 + 0.5)
    k.rect((520, 220, 900, 760), fill=(16, 20, 28), outline=GOLD, w=2, r=20, a=b)
    k.text((710, 260), "SAMUEL PLIMSOLL", 30, WHITE, a=b, anchor="ma")
    k.text((710, 310), "fought for the mark", 24, GREY, a=b, anchor="ma", bold=False)
    k.text((710, 400), "1876", 110, GOLD, a=seg(t, d*0.6, d*0.6 + 0.4), anchor="ma")
    k.text((710, 540), "BRITISH LAW:", 28, WHITE, a=seg(t, d*0.7, d*0.7 + 0.4), anchor="ma")
    k.text((710, 585), "COMPULSORY", 34, GREEN, a=seg(t, d*0.7, d*0.7 + 0.4), anchor="ma")
    k.check((710, 680), 34, GREEN, 8, a=seg(t, d*0.78, d*0.78 + 0.3), prog=seg(t, d*0.78, d*0.78 + 0.5))

SCENES = [scene0, scene1, scene2]
