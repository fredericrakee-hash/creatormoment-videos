# Animated explanation for the solution video of Quiz #22 (ice falling off a rocket). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

LOX = (70, 150, 255); WALL = (190, 195, 205); ICE = (225, 240, 255)

def tank(k, a=1.0):
    k.rect((80, 160, 420, 820), fill=(25, 55, 110), a=a)
    k.rect((420, 160, 444, 820), fill=WALL, a=a)
    k.text((250, 190), "INSIDE", 26, GREY, a=a, anchor="ma", bold=False)
    k.text((680, 190), "OUTSIDE", 26, GREY, a=a, anchor="ma", bold=False)

def scene0(k, t, d):
    k.tag((60, 50), "SUPER-COLD OXYGEN", BLUE, a=seg(t, 0, 0.4))
    tank(k, seg(t, 0.1, 0.5))
    # sloshing liquid
    lv = 330
    pts = [(80 + x, lv + 6*math.sin(x/30 + t*3)) for x in range(0, 341, 10)]
    k.shape(pts + [(420, 820), (80, 820)], fill=LOX + (220,), a=seg(t, 0.3, 0.8))
    k.text((250, 440), "LIQUID OXYGEN", 32, WHITE, a=seg(t, 0.5, 0.9), anchor="ma")
    k.text((250, 500), "below −183 °C", 44, WHITE, a=seg(t, 0.8, 1.2), anchor="ma")
    k.text((250, 560), "(−297 °F)", 30, WHITE, a=seg(t, 1.0, 1.4), anchor="ma", bold=False)
    k.text((680, 440), "WARM AIR", 32, GOLD, a=seg(t, 1.4, 1.8), anchor="ma")
    k.text((680, 500), "+25 °C", 44, GOLD, a=seg(t, 1.6, 2.0), anchor="ma")
    w = seg(t, d*0.65, d*0.65 + 0.4)
    k.arrow((620, 700), (452, 700), RED, 5, prog=w, head=18)
    k.text((640, 680), "BARE METAL WALL", 26, RED, a=w, bold=False)
    k.text((640, 720), "NO INSULATION", 26, RED, a=w, bold=False)

def scene1(k, t, d):
    k.tag((60, 50), "HUMID AIR FREEZES ON", GOLD, a=seg(t, 0, 0.4))
    tank(k)
    k.rect((80, 330, 420, 820), fill=LOX + (200,))
    # vapour dots drifting toward the wall, freezing into a growing crust
    grow = seg(t, 0.6, d - 0.5)
    th = 8 + 60*grow
    k.rect((444, 160, 444 + th, 820), fill=ICE, a=seg(t, 0.4, 0.8))
    for i in range(46):
        ph = (t*0.45 + i*0.137) % 1.0
        y = 180 + (i*97) % 620
        x = lerp(900, 444 + th + 6, ph)
        k.circle((x, y), 6, fill=BLUE, a=(1 - ph)*0.9 + 0.1)
    for i in range(int(30*grow)):
        y = 180 + (i*53) % 620; x = 444 + th*((i*37) % 10)/10
        k.line((x - 7, y), (x + 7, y), WHITE, 2); k.line((x, y - 7), (x, y + 7), WHITE, 2)
    k.text((690, 820), "WATER VAPOR", 26, BLUE, a=seg(t, 0.5, 0.9), anchor="ma", bold=False)
    k.text((690, 120), "→ FROST + ICE", 34, ICE, a=seg(t, 1.6, 2.0), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "SHAKEN LOOSE AT LIFTOFF", GOLD, a=seg(t, 0, 0.4))
    k.clip(0.62, (0, 0, 960, 880), dim=0.25)
    # vibration + airflow
    k.arrow((140, 300), (140, 640), BLUE, 5, prog=seg(t, 0.5, 1.0), head=18)
    k.arrow((200, 300), (200, 640), BLUE, 5, prog=seg(t, 0.6, 1.1), head=18)
    k.text((60, 250), "AIRFLOW", 28, BLUE, a=seg(t, 0.5, 0.9))
    sh = 6*math.sin(t*40)*seg(t, 0.9, 1.3)
    k.text((760 + sh, 250), "SHAKING", 28, GOLD, a=seg(t, 0.9, 1.3), anchor="ma")
    # chunks falling
    for i in range(14):
        ph = ((t - 1.0)*0.5 + i*0.13) % 1.0
        if t < 1.0: break
        x = 430 + (i*41) % 160 + ph*60*math.sin(i)
        y = lerp(260, 840, ph*ph)
        r = 8 + (i % 4)*4
        k.shape([(x - r, y), (x, y - r*0.6), (x + r, y + r*0.2), (x - r*0.3, y + r*0.7)], fill=ICE, a=1 - ph*0.5)
    v = seg(t, d*0.5, d*0.5 + 0.4)
    k.rect((60, 700, 900, 850), fill=(10, 13, 20, 210), r=18, a=v)
    k.text((480, 720), "WHITE WISPS BEFORE LAUNCH:", 26, GREY, a=v, anchor="ma", bold=False)
    k.text((480, 770), "OXYGEN BOILING OFF → FOG", 34, WHITE, a=v, anchor="ma")

SCENES = [scene0, scene1, scene2]
