# Animated explanation for the solution video of Quiz #15 (icebreaker). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

HULL = (170, 40, 35); ICE = (225, 238, 248); SEA = (30, 70, 110)
WL = 520  # waterline y

def water(k, a=1.0):
    k.rect((40, WL, 920, 820), fill=(*SEA, 255), a=a*0.9)

def ship(k, x, lift=0.0, a=1.0, pitch=0.0):
    """side view, bow pointing right; x = bow tip; lift raises the bow (px), hull pivots about the stern"""
    st = x - 560
    def P(px, py): return (px, py - lift*max(0.0, px - st)/560)
    top, keel = WL - 110, WL + 60
    prof = [P(x, top)] + [P(x - 170*(1 - math.cos(u*math.pi/2)), top + (keel - top)*math.sin(u*math.pi/2)) for u in (0.2, 0.4, 0.6, 0.8, 1.0)]
    pts = prof + [P(st, keel), P(st, top)]
    k.shape(pts, fill=HULL, outline=WHITE, w=2, a=a)
    sx = st + 60
    k.shape([P(sx, top), P(sx, top - 110), P(sx + 170, top - 110), P(sx + 170, top)], fill=(230, 230, 225), outline=WHITE, w=2, a=a)

def ice(k, x0, x1, broken=0.0, sag=0.0, a=1.0):
    if broken <= 0:
        k.rect((x0, WL - 14 + sag, x1, WL + 26 + sag), fill=ICE, outline=WHITE, w=2, a=a)
    else:
        n = 5; w = (x1 - x0)/n
        for i in range(n):
            dx = i*w; tilt = (i % 2*2 - 1)*14*broken
            p = [(x0 + dx + 4, WL - 14 + tilt), (x0 + dx + w - 4, WL - 14 - tilt), (x0 + dx + w - 4, WL + 26 - tilt), (x0 + dx + 4, WL + 26 + tilt)]
            k.shape(p, fill=ICE, outline=WHITE, w=2, a=a)

def scene0(k, t, d):
    k.tag((60, 50), "IT DOESN'T CUT", GOLD, a=seg(t, 0, 0.4))
    water(k)
    m = seg(t, 0.3, d*0.8)
    bow = lerp(470, 720, m)
    lift = max(0.0, bow - 520)*0.6
    ship(k, bow, lift)
    ice(k, 520, 920)
    k.text((80, 150), "ROUNDED, SLOPED BOW", 34, WHITE, a=seg(t, 0.6, 1.0))
    v = seg(t, d*0.55, d*0.55 + 0.4)
    k.arrow((bow - 10, WL - 140 - lift), (bow + 80, WL - 200 - lift), GREEN, 6, prog=v, a=v)
    k.text((80, 210), "SLIDES UP ONTO THE ICE", 34, GREEN, a=v)

def scene1(k, t, d):
    k.tag((60, 50), "WEIGHT DOES THE WORK", BLUE, a=seg(t, 0, 0.4))
    water(k)
    br = seg(t, d*0.5, d*0.5 + 0.5)
    lift = lerp(120, 40, br)
    ship(k, 720, lift)
    ice(k, 520, 920, broken=br)
    for j, x in enumerate((480, 580, 680)):
        v = seg(t, 0.4 + j*0.2, 0.9 + j*0.2)
        k.arrow((x, 180), (x, 300 - lift*0.6), RED, 7, prog=v, a=v)
    k.text((480, 130), "THOUSANDS OF TONNES", 34, WHITE, a=seg(t, 0.4, 0.8), anchor="ma")
    for j, (cx, cy) in enumerate(((640, WL + 40), (760, WL + 30))):
        k.line((cx - 20, cy - 30), (cx + 10, cy + 10), GOLD, 5, prog=br, a=br)
    k.text((480, 720), "THE ICE CRACKS", 38, GOLD, a=br, anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "AN OPEN CHANNEL", GREEN, a=seg(t, 0, 0.4))
    # top view: lane behind the ship
    k.rect((40, 260, 920, 820), fill=ICE, a=1.0)
    m = seg(t, 0.2, d*0.85)
    y_bow = lerp(780, 400, m)
    k.rect((380, y_bow, 580, 820), fill=SEA, a=1.0)
    # broken floes along the channel edges
    for i in range(10):
        yy = y_bow + 40 + i*55
        if yy > 800: break
        for side, xx in ((0, 350), (1, 610)):
            off = (i*37 % 17) - 8
            k.rect((xx - 22 + off, yy, xx + 22 + off, yy + 30), fill=(205, 222, 235), outline=WHITE, w=2)
    k.shape([(480, y_bow - 80), (560, y_bow), (560, y_bow + 220), (400, y_bow + 220), (400, y_bow)], fill=HULL, outline=WHITE, w=2)
    for s in (-1, 1):
        k.arrow((480 + s*90, y_bow + 60), (480 + s*170, y_bow + 40), GOLD, 5, a=seg(t, 0.6, 1.0))
    v = seg(t, d*0.55, d*0.55 + 0.4)
    k.text((480, 140), "OTHER SHIPS FOLLOW", 36, GREEN, a=v, anchor="ma")
    k.check((800, 170), 30, GREEN, 7, a=v, prog=v)

SCENES = [scene0, scene1, scene2]
