import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade
from warm import warm

W, H, FPS = 1080, 1920, 30
NUM = 30
DUR = 48.5
CUTS = {"A": (0.0, 6.6), "B": (6.6, 14.9), "C": (14.9, 20.0), "D": (20.0, 28.8)}
END3D = 28.8
BASE = QDIR
META = {int(k): v for k, v in json.load(open(f"{BASE}/meta.json")).items()}
FD = "/usr/share/fonts/opentype/inter/"
def F(n, s): return ImageFont.truetype(FD+n, s)
F_TITLE = F("InterDisplay-Black.otf", 92)
F_SUB = F("Inter-SemiBold.otf", 52)
F_TAG = F("Inter-SemiBold.otf", 30)
F_LAB = F("Inter-SemiBold.otf", 34)
F_Q = F("InterDisplay-Black.otf", 80)
F_OPT = F("InterDisplay-Black.otf", 58)
F_LET = F("InterDisplay-Black.otf", 60)
F_SMALL = F("Inter-SemiBold.otf", 38)
GOLD = (255, 200, 90)
BLUE = (140, 200, 255)

def ease(x):
    x = max(0, min(1, x)); return x*x*(3-2*x)

import sys as _s; _s.path.insert(0, "/home/claude/creatormoment-videos/pipeline")
try:
    from subs import make_subs
    _L = {}; exec(open(f"{QDIR}/voice.py").read().split("d = {}")[0].split('V = "am_michael"')[1], {}, _L)
    SUBS = make_subs(QDIR, {"v1": 0.3, "v2": 6.8, "v3": 15.0, "v4": 20.1}, {k: v[1] for k, v in _L["lines"].items()})
except Exception:
    SUBS = json.load(open(f"{QDIR}/subs.json"))
OPTS = [("A", "To keep the switches from freezing", 32.0), ("B", "To warn cars at the crossing", 34.7), ("C", "To burn off spilled diesel", 37.5), ("D", "To keep track workers warm", 39.8)]
VOICE_END = 42.4
def _fit():
    d = ImageDraw.Draw(Image.new("RGB", (8, 8))); sz = 58
    while sz > 34 and max(d.textlength(o[1], font=F("InterDisplay-Black.otf", sz)) for o in OPTS) > W-180-200: sz -= 2
    return F("InterDisplay-Black.otf", sz)
RED = (255, 110, 80)

F_OPT_FIT = None
def shadow_text(base, xy, txt, font, fill=(255, 255, 255), blur=6, sh=170, anchor="la", alpha=1.0):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((xy[0]+2, xy[1]+3), txt, font=font, fill=(0, 0, 0, sh), anchor=anchor)
    lay = lay.filter(ImageFilter.GaussianBlur(blur))
    ImageDraw.Draw(lay).text(xy, txt, font=font, fill=fill, anchor=anchor)
    if alpha < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v*alpha)))
    base.alpha_composite(lay)

def wrap(d, txt, font, maxw):
    out, cur = [], ""
    for w_ in txt.split():
        t_ = (cur+" "+w_).strip()
        if d.textlength(t_, font=font) > maxw and cur: out.append(cur); cur = w_
        else: cur = t_
    return out + [cur]

def shot_of(i):
    t = i/FPS
    for k, (a, b) in CUTS.items():
        if a <= t < b: return k, int(round(a*FPS))
    return "D", int(round(CUTS["D"][0]*FPS))

_cache = {}
def _src(i):
    p = f"{BASE}/frames/f{i:04d}.png"
    if os.path.exists(p): return p
    s, i0 = shot_of(i)
    q = f"{BASE}/interp/{s}/{i-i0+1:05d}.jpg"
    if os.path.exists(q): return q
    k = i - (i % 2)
    while k >= 0 and not os.path.exists(f"{BASE}/frames/f{k:04d}.png"): k -= 1
    return f"{BASE}/frames/f{max(k,0):04d}.png"
def frame3d(i):
    i = max(0, min(i, int(END3D*FPS)-1))
    if i not in _cache:
        if len(_cache) > 4: _cache.clear()
        _cache[i] = warm(grade(Image.open(_src(i)), i, horizon_y=5000))
    return _cache[i]

def brand(fr):
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([56, 112, 262, 166], radius=12, fill=(0, 0, 0, 120), outline=(255, 255, 255, 90), width=2)
    d.text((159, 139), f"QUIZ #{NUM}", font=F_TAG, fill=(255, 255, 255), anchor="mm")

def callout(fr, pt, label, a, lx=120, ly=1180, col=GOLD):
    if a <= 0 or pt is None: return
    fx, fy, fz = pt
    if fz <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    tw = d.textlength(label, font=F_SMALL)
    d.line([(lx+tw+14, ly+22), (fx, fy)], fill=col+(int(230*a),), width=4)
    d.ellipse([fx-14, fy-14, fx+14, fy+14], outline=col+(int(255*a),), width=4)
    fr.alpha_composite(lay)
    shadow_text(fr, (lx, ly), label, F_SMALL, fill=col, alpha=a)

def P(m, k):
    v = m.get(k); return v if v and v[2] > 0 else None

def dashed(d, p, q, col, w=4, dash=18, gap=14):
    import math as _m
    L = _m.hypot(q[0]-p[0], q[1]-p[1]); n = int(L/(dash+gap)) + 1
    for k in range(n):
        a0 = k*(dash+gap)/L; a1 = min(1, (k*(dash+gap)+dash)/L)
        if a0 >= 1: break
        d.line([(p[0]+(q[0]-p[0])*a0, p[1]+(q[1]-p[1])*a0), (p[0]+(q[0]-p[0])*a1, p[1]+(q[1]-p[1])*a1)], fill=col, width=w)

def tag(fr, txt, t0, t1, t, x=70, y=250, col=(255, 120, 100)):
    a = ease((t-t0)/0.4)*(1-ease((t-t1)/0.3))
    if a > 0: shadow_text(fr, (x, y), txt, F_TAG, fill=col, alpha=a*(1.0 if int(t*2.5) % 2 == 0 else 0.45))

def hud(fr, t, rows, a, x=70, y=320):
    """cab-display style readout: rows = [(label, value, colour)]"""
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    h = 30 + 66*len(rows)
    d.rounded_rectangle([x, y, x + 560, y + h], radius=16, fill=(6, 10, 14, int(150*a)), outline=(255, 255, 255, int(70*a)), width=2)
    fr.alpha_composite(lay)
    for k, (lab, val, col) in enumerate(rows):
        shadow_text(fr, (x + 26, y + 22 + k*66), lab, F_TAG, fill=(190, 198, 210), alpha=a)
        shadow_text(fr, (x + 534, y + 14 + k*66), val, F("InterDisplay-Black.otf", 44), fill=col, anchor="ra", alpha=a)

import random as _r
_fr = _r.Random(4)
FLAKES = [(_fr.uniform(0, W), _fr.uniform(0, H), _fr.uniform(60, 200), _fr.uniform(1.2, 4.5), _fr.uniform(0, 6.28)) for _ in range(260)]
def snow(fr, t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0)); db = ImageDraw.Draw(big)
    for (x0, y0, sp, r, ph) in FLAKES:
        y = (y0 + t*sp) % H; x = (x0 + 30*math.sin(t*0.8 + ph) + t*12) % W
        if r > 3.5:
            db.ellipse([x-r*1.6, y-r*1.6, x+r*1.6, y+r*1.6], fill=(255, 255, 255, 120))
        else:
            d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, 150))
    fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.8)))
    fr.alpha_composite(big.filter(ImageFilter.GaussianBlur(4)))

def intro(fr, t, m):
    a = ease((t-0.3)/0.4)*(1-ease((t-6.4)/0.3))
    if a <= 0: return
    FT = F("InterDisplay-Black.otf", 74)
    shadow_text(fr, (60, 200), "CHICAGO.", FT, alpha=a)
    shadow_text(fr, (60, 285), "DEEP WINTER.", FT, fill=BLUE, alpha=a*ease((t-1.6)/0.4))
    hud(fr, t, [("AIR TEMPERATURE", "−20 °C", (255, 255, 255)), ("", "−4 °F", (200, 205, 215))], a*ease((t-2.4)/0.4), y=420)
    if m: callout(fr, P(m, "switch"), "COMMUTER RAIL LINE", a*ease((t-4.0)/0.4), lx=90, ly=1400, col=(255, 255, 255))

def flamepanel(fr, t, m):
    a = ease((t-6.8)/0.4)*(1-ease((t-14.7)/0.3))
    if a <= 0: return
    tag(fr, "● TRACK LEVEL", 6.7, 14.7, t)
    if m:
        callout(fr, P(m, "points"), "ONE TRACK SPLITS INTO TWO", a*ease((t-7.4)/0.4)*(1-ease((t-10.0)/0.3)), lx=90, ly=1400, col=(255, 255, 255))
        callout(fr, P(m, "flames"), "FLAMES ALONG THE RAILS", a*ease((t-10.6)/0.4), lx=90, ly=1400, col=GOLD)

def trainpanel(fr, t, m):
    a = ease((t-15.0)/0.4)*(1-ease((t-19.8)/0.3))
    if a <= 0: return
    tag(fr, "● COMMUTER TRAIN · 50 km/h", 14.9, 19.8, t)
    if m: callout(fr, P(m, "train"), "STRAIGHT THROUGH THE FIRE", a*ease((t-16.0)/0.4), lx=90, ly=1400, col=GOLD)

def afterpanel(fr, t, m=None):
    a = ease((t-20.2)/0.4)*(1-ease((t-28.6)/0.3))
    if a <= 0: return
    pop = 0.85 + 0.15*ease((t-20.2)/0.25)
    shadow_text(fr, (W//2, 260), "LIT ON PURPOSE.", F("InterDisplay-Black.otf", int(80*pop)), anchor="ma", alpha=a)
    shadow_text(fr, (W//2, 360), "EVERY WINTER.", F("InterDisplay-Black.otf", int(84*pop)), fill=GOLD, anchor="ma", alpha=a*ease((t-21.4)/0.3))
    b_ = ease((t-24.6)/0.4)
    shadow_text(fr, (W//2, 1250), "300+ TRAINS A DAY", F_SUB, fill=GOLD, anchor="ma", alpha=a*b_)
    shadow_text(fr, (W//2, 1320), "THROUGH ONE JUNCTION", F_SUB, anchor="ma", alpha=a*b_)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(min(i, int(END3D*FPS)-1))
    brand(fr)
    snow(fr, t)
    intro(fr, t, m); flamepanel(fr, t, m); trainpanel(fr, t, m)
    for c in (6.6, 14.9, 20.0):
        if c <= t < c+0.15:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-c)/0.15)))))
    afterpanel(fr, t, m)
    cur = [s for s in SUBS if s[0] <= t < s[1]]
    if cur:
        txt = cur[-1][2]; d = ImageDraw.Draw(fr)
        for k, ln in enumerate(wrap(d, txt, F_SUB, W-140)):
            shadow_text(fr, (W//2, 1560 + k*64), ln, F_SUB, anchor="ma")
    if t > END3D-0.6:
        fr = Image.blend(fr, quiz_bg(), ease((t-END3D+0.6)/0.6))
    return fr

_qbg = None
def quiz_bg():
    global _qbg
    if _qbg is None:
        last = frame3d(int(END3D*FPS)-2).convert("RGB")
        _qbg = Image.blend(last.filter(ImageFilter.GaussianBlur(26)), Image.new("RGB", (W, H), (6, 8, 14)), 0.62).convert("RGBA")
    return _qbg

def quiz_frame(i):
    global F_OPT_FIT
    if F_OPT_FIT is None: F_OPT_FIT = _fit()
    t = i/FPS
    fr = quiz_bg().copy(); brand(fr)
    qa = ease((t-END3D)/0.5)
    shadow_text(fr, (W//2, 360), "WHY ARE THERE FLAMES", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 455), "ON THE TRACKS?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
    for k, (L, txt, ts) in enumerate(OPTS):
        p = ease((t-ts+0.05)/0.35)
        if p <= 0: continue
        y = 680 + k*200; x0 = 90 + int((1-p)*-120); x1 = W-90 + int((1-p)*-120)
        speaking = ts <= t < ts + 2.0 and t < VOICE_END
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x0, y, x1, y+160], radius=28, fill=(255, 255, 255, int(30*p)),
                             outline=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(110*p)), width=4 if speaking else 2)
        ld.ellipse([x0+26, y+24, x0+138, y+136], fill=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(235*p)))
        ld.text((x0+82, y+80), L, font=F_LET, fill=(8, 10, 16, int(255*p)), anchor="mm")
        ld.text((x0+170, y+80), txt, font=F_OPT_FIT, fill=(255, 255, 255, int(255*p)), anchor="lm")
        fr.alpha_composite(lay)
    if t > VOICE_END:
        a = ease((t-VOICE_END)/0.4)
        shadow_text(fr, (W//2, 1520), "COMMENT YOUR ANSWER ↓", F_SUB, anchor="ma", alpha=a)
        shadow_text(fr, (W//2, 1600), "Solution tomorrow · Follow so you don't miss it", F_SMALL, fill=(200, 205, 215), anchor="ma", alpha=a)
    return fr

def draw(i):
    return (scene_frame(i) if i/FPS < END3D else quiz_frame(i)).convert("RGB")

def clean_clip(out, t0, t1):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(int(t0*FPS), int(t1*FPS)): p.stdin.write(frame3d(i).convert("RGB").tobytes())
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for tt in sys.argv[2].split(","):
            draw(int(float(tt)*FPS)//2*2).save(f"{BASE}/still_{tt}.png")
        sys.exit()
    if sys.argv[1] == "clean":
        clean_clip(sys.argv[2], float(sys.argv[3]), float(sys.argv[4])); sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", sys.argv[1]], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)): p.stdin.write(draw(i).tobytes())
    p.stdin.close(); sys.exit(p.wait())
