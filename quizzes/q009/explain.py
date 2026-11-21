# Animated explanation for the solution video of Quiz #9 (bolter). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, lerp2, ease

DECK_Y, X0, X1, SEA = 620, 40, 880, 790
WIRES = [260, 305, 350, 395]

def jet(k, x, y, ang=0.0, s=1.6, a=1.0, hook=False):
    def tr(p):
        c, si = math.cos(ang), math.sin(ang)
        return (x + s*(p[0]*c - p[1]*si), y + s*(p[0]*si + p[1]*c))
    body = [(62, -2), (44, -9), (-38, -10), (-58, -34), (-68, -34), (-60, -8), (-64, 4), (36, 6)]
    wing = [(14, 0), (-22, 0), (-30, 7), (2, 7)]
    k.shape([tr(p) for p in body], fill=(205, 210, 218), a=a)
    k.shape([tr(p) for p in wing], fill=(120, 126, 136), a=a)
    k.shape([tr(p) for p in [(42, -8), (30, -13), (18, -9)]], fill=(40, 60, 80), a=a)
    if hook: k.line(tr((-50, 4)), tr((-62, 18)), GOLD, 3, a=a)

def carrier(k, t, hi_wires=0.0, wire_col=GOLD):
    k.waves(20, 940, SEA + 6, amp=5, n=12, col=BLUE, w=3, t=t, a=0.7)
    k.shape([(X0, DECK_Y), (X1, DECK_Y), (X1 - 30, SEA), (X0 + 40, SEA)], fill=(70, 76, 86))
    k.line((X0, DECK_Y), (X1, DECK_Y), WHITE, 4)
    k.shape([(600, DECK_Y), (600, 480), (680, 480), (692, DECK_Y)], fill=(90, 96, 106))   # island
    for w in WIRES:
        col = tuple(int(lerp(c0, c1, hi_wires)) for c0, c1 in zip((180, 180, 180), wire_col))
        k.line((w, DECK_Y - 2), (w, DECK_Y - 16), col, 7)

def scene0(k, t, d):
    carrier(k, t, hi_wires=seg(t, 0.5, 1.2))
    k.tag((60, 50), "LANDING ON THE CARRIER", WHITE, a=seg(t, 0, 0.4))
    k.text((150, 470), "ARRESTING WIRES", 30, GOLD, a=seg(t, 0.6, 1.0), bold=False)
    k.line((300, 512), (320, 590), GOLD, 2, a=seg(t, 0.6, 1.0))
    # glide path, touching down beyond the last wire
    p0, p1 = (-60, 200), (470, DECK_Y - 20)
    k.poly([p0, p1], WHITE, 3, prog=seg(t, 0.2, 2.6), dash=(14, 12), a=0.6)
    u = seg(t, 0.2, 2.6)
    jx, jy = lerp2(p0, p1, u)
    if t > 2.6:
        jx = 470 + 60*seg(t, 2.6, 3.6); jy = DECK_Y - 20
    jet(k, jx, jy, ang=math.atan2(p1[1]-p0[1], p1[0]-p0[0]) if t < 2.6 else 0.0, hook=True)
    a = seg(t, 2.9, 3.3)
    k.cross((328, 670), 30, RED, 8, a=a)
    k.text((480, 340), "HOOK MISSES EVERY WIRE", 40, RED, a=a, anchor="ma")
    k.text((480, 200), "= A “BOLTER”", 64, GOLD, a=seg(t, max(3.6, d*0.62), max(4.0, d*0.62 + 0.4)), anchor="ma")

def scene1(k, t, d):
    carrier(k, t)
    k.tag((60, 50), "THROTTLE AT IDLE", RED, a=seg(t, 0, 0.4))
    # rolls to the end of the deck, then falls off
    if t < 2.6:
        x = lerp(530, X1, seg(t, 0.0, 2.6)*0.92 + 0.08*min(1, t/2.6)); jet(k, x, DECK_Y - 20, hook=True)
    else:
        u = min(1.0, (t - 2.6)/1.3)
        x = X1 + 40*u; y = DECK_Y - 20 + 190*u*u; ang = 1.1*u
        if u < 1: jet(k, x, y, ang=ang, hook=True)
        k.poly([(X1 + 40*v, DECK_Y - 20 + 190*v*v) for v in [i/20 for i in range(21)]], RED, 3, prog=u, dash=(10, 10))
    sp = seg(t, 3.9, 4.4)
    if sp > 0:
        for r in (18, 34, 52):
            k.circle((X1 + 30, SEA + 4), r*sp, outline=WHITE, w=3, a=1 - 0.6*sp)
        k.text((480, 260), "NOT ENOUGH SPEED", 50, RED, a=sp, anchor="ma")
        k.text((480, 330), "TO FLY AGAIN", 50, RED, a=sp, anchor="ma")

def throttle(k, level, a, label_col=GOLD):
    k.text((100, 118), "THROTTLE", 22, WHITE, a=a, anchor="ma", bold=False)
    k.rect((60, 150, 140, 410), fill=(0, 0, 0, 140), outline=WHITE, w=2, r=14, a=a)
    k.text((100, 172), "FULL", 22, GREEN, a=a, anchor="ma", bold=False)
    k.text((100, 380), "IDLE", 22, RED, a=a, anchor="ma", bold=False)
    k.line((100, 210), (100, 370), GREY, 6, a=a)
    y = lerp(370, 210, level)
    k.rect((72, y - 14, 128, y + 14), fill=label_col, r=8, a=a)

def scene2(k, t, d):
    carrier(k, t)
    half = d*0.55
    k.tag((60, 50), "FULL POWER" if t < half else "HOOK CAUGHT", GREEN if t < half else GOLD, a=seg(t, 0, 0.4))
    if t < half:
        throttle(k, 1.0, seg(t, 0, 0.4))
        u = seg(t, 0.0, half - 0.3)
        path = [(470, DECK_Y - 20), (X1 - 40, DECK_Y - 20), (1000, DECK_Y - 130)]
        k.poly(path, GREEN, 4, prog=u, dash=(14, 10))
        # jet position along the path
        L = [math.dist(path[i], path[i+1]) for i in range(len(path)-1)]; tot = sum(L); lim = tot*u; acc = 0
        for i, l in enumerate(L):
            if acc + l >= lim:
                f = (lim - acc)/l; p = lerp2(path[i], path[i+1], f)
                ang = math.atan2(path[i+1][1]-path[i][1], path[i+1][0]-path[i][0]); break
            acc += l
        else:
            p, ang = path[-1], math.atan2(path[-1][1]-path[-2][1], path[-1][0]-path[-2][0])
        jet(k, p[0], p[1], ang=ang, hook=True)
        ar = seg(t, half*0.5, half*0.85)
        if ar > 0:
            k.arc((540, 270), 80, -60, -60 + 300*ar, GREEN, 7)
            e = math.radians(-60 + 300*ar)
            k.arrow((540 + 80*math.cos(e - 0.3), 270 + 80*math.sin(e - 0.3)), (540 + 80*math.cos(e), 270 + 80*math.sin(e)), GREEN, 7, head=26)
        k.text((540, 390), "FLIES OFF, CIRCLES AROUND", 38, GREEN, a=seg(t, half*0.55, half*0.55 + 0.4), anchor="ma")
        k.text((540, 440), "AND TRIES AGAIN", 38, GREEN, a=seg(t, half*0.7, half*0.7 + 0.4), anchor="ma")
    else:
        lt = t - half
        throttle(k, 1.0 - seg(lt, 0.9, 1.7), 1.0)
        x = lerp(300, 440, seg(lt, 0.0, 0.9)); jet(k, x, DECK_Y - 20, hook=False)
        k.line((x - 85, DECK_Y - 8), (350, DECK_Y - 4), GOLD, 4, a=seg(lt, 0.0, 0.3))
        k.line((350, DECK_Y - 2), (350, DECK_Y - 16), GOLD, 8)
        k.check((540, 300), 44, GREEN, 10, prog=seg(lt, 1.0, 1.5))
        k.text((540, 390), "STOPPED → BACK TO IDLE", 40, WHITE, a=seg(lt, 1.2, 1.6), anchor="ma")

SCENES = [scene0, scene1, scene2]
