# Animated explanation for the solution video of Quiz #14 (satellite foil / multi-layer insulation). Drawn with pipeline/explain_kit.py.
import math
from explain_kit import WHITE, GOLD, GREEN, RED, BLUE, GREY, seg, lerp, ease

FOIL = (215, 170, 70); BODY = (90, 95, 105)

def scene0(k, t, d):
    k.tag((60, 50), "SUN SIDE VS. SHADOW SIDE", GOLD, a=seg(t, 0, 0.4))
    a = seg(t, 0.1, 0.5)
    # sun on the left with rays
    k.circle((90, 420), 60, fill=(255, 210, 100), a=a)
    for i in range(6):
        y = 250 + i*70
        k.arrow((170, y), (330, y), GOLD, 4, prog=seg(t, 0.3 + i*0.08, 0.8 + i*0.08), head=14)
    # satellite box
    k.rect((360, 300, 600, 540), fill=BODY, outline=WHITE, w=2, a=a)
    k.rect((600, 300, 900, 540), fill=(60, 80, 130), outline=BLUE, w=2, a=a*0.5)
    k.text((750, 405), "SHADOW", 28, BLUE, a=a, anchor="ma", bold=False)
    k.text((360, 590), "+150 °C", 54, RED, a=seg(t, 0.8, 1.2))
    k.text((360, 655), "(+300 °F)", 28, RED, a=seg(t, 0.9, 1.3), bold=False)
    k.text((640, 590), "−130 °C", 54, BLUE, a=seg(t, 1.4, 1.8))
    k.text((640, 655), "(−200 °F)", 28, BLUE, a=seg(t, 1.5, 1.9), bold=False)
    k.text((480, 790), "AT THE SAME TIME", 34, WHITE, a=seg(t, d*0.6, d*0.6 + 0.4), anchor="ma")

def scene1(k, t, d):
    k.tag((60, 50), "MULTI-LAYER INSULATION", GREEN, a=seg(t, 0, 0.4))
    # stack of thin layers (exploded view)
    n = 8
    for i in range(n):
        a = seg(t, 0.2 + i*0.08, 0.5 + i*0.08)
        y = 250 + i*34
        k.rect((250, y, 550, y + 10), fill=(220, 220, 228), outline=FOIL, w=2, a=a)
    k.text((580, 250), "PLASTIC FILM", 28, WHITE, a=seg(t, 0.9, 1.3))
    k.text((580, 290), "+ ALUMINIUM", 28, GREY, a=seg(t, 1.0, 1.4), bold=False)
    # incoming heat reflected
    p = seg(t, 1.3, 2.0)
    k.text((580, 330), "COATING", 28, GREY, a=seg(t, 1.0, 1.4), bold=False)
    k.arrow((80, 150), (240, 250), RED, 5, prog=p, head=16)
    k.arrow((240, 250), (80, 360), GOLD, 5, prog=seg(t, 1.9, 2.5), head=16)
    k.text((60, 115), "SUNLIGHT", 26, RED, a=p, bold=False)
    k.text((60, 380), "REFLECTED", 26, GOLD, a=seg(t, 2.0, 2.4), bold=False)
    # warmth kept inside (below)
    q = seg(t, d*0.55, d*0.55 + 0.5)
    k.rect((250, 560, 550, 700), fill=BODY, outline=WHITE, w=2, a=q)
    k.text((400, 615), "WARM INSIDE", 30, GOLD, a=q, anchor="ma")
    for i in range(3):
        x = 320 + i*80
        k.arrow((x, 560), (x, 540 - 20*q), GOLD, 4, prog=q, head=12)
        k.cross((x, 525), 12, RED, 4, a=seg(t, d*0.7, d*0.7 + 0.3))
    k.text((480, 760), "HEAT CAN'T GET IN – OR OUT", 34, GREEN, a=seg(t, d*0.75, d*0.75 + 0.4), anchor="ma")

def scene2(k, t, d):
    k.tag((60, 50), "GOLD COLOUR = PLASTIC FILM", GOLD, a=seg(t, 0, 0.4))
    k.clip(0.5, (0, 0, 960, 880), dim=0.35)
    v = seg(t, 0.5, 0.9)
    k.rect((90, 560, 870, 820), fill=(10, 13, 20, 215), r=18, a=v)
    k.text((480, 590), "AMBER POLYIMIDE FILM", 38, FOIL, a=v, anchor="ma")
    k.text((480, 650), "+ SILVER ALUMINIUM BEHIND IT", 32, WHITE, a=seg(t, 0.9, 1.3), anchor="ma", bold=False)
    w = seg(t, d*0.55, d*0.55 + 0.4)
    k.cross((300, 750), 22, RED, 6, a=w)
    k.text((340, 728), "USUALLY NO REAL GOLD", 32, WHITE, a=w)

SCENES = [scene0, scene1, scene2]
