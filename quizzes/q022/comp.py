import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
NUM = 22
DUR = 50.5
CUTS = {"A": (0.0, 7.0), "B": (7.0, 16.4), "C": (16.4, 22.5), "D": (22.5, 31.0)}
END3D = 31.0
HOR = {"A": 1250, "B": 5000, "C": 1300, "D": 5000}
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
    SUBS = make_subs(QDIR, {"v1": 0.3, "v2": 7.2, "v3": 16.7, "v4": 25.8}, {k: v[1] for k, v in _L["lines"].items()})
except Exception:
    SUBS = json.load(open(f"{QDIR}/subs.json"))
OPTS = [("A", "Ice from the super-cold fuel", 34.0), ("B", "Paint peeling off in the heat", 36.6), ("C", "Foam from the launch pad water", 39.0), ("D", "Pieces of the heat shield", 41.4)]
VOICE_END = 43.7
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
        _cache[i] = grade(Image.open(_src(i)), i, horizon_y=HOR[shot_of(i)[0]])
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
    d.line([(lx+200, ly+50), (fx, fy)], fill=col+(int(230*a),), width=4)
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

def intro(fr, t, m):
    a = ease((t-0.3)/0.4)*(1-ease((t-6.7)/0.3))
    if a <= 0: return
    FT = F("InterDisplay-Black.otf", 74)
    shadow_text(fr, (60, 230), "MINUTES BEFORE", FT, alpha=a)
    shadow_text(fr, (60, 315), "LIFTOFF.", FT, fill=GOLD, alpha=a*ease((t-1.0)/0.4))
    tag(fr, "● FLORIDA · LAUNCH PAD", 0.3, 6.7, t, y=430)
    if m: callout(fr, P(m, "frost"), "LOOK HERE", a*ease((t-3.6)/0.4), lx=90, ly=1250, col=GOLD)

def closepanel(fr, t, m):
    a = ease((t-7.3)/0.4)*(1-ease((t-16.2)/0.3))
    if a <= 0: return
    tag(fr, "● CLOSE-UP · 300 mm", 7.2, 16.2, t)
    rows = ((9.4, "ROUGH, CRUSTY LAYER", (255, 255, 255)), (13.2, "WHITE VAPOR DRIFTING OFF", GOLD))
    for k, (ts, txt, col) in enumerate(rows):
        b_ = ease((t-ts)/0.3)
        shadow_text(fr, (70 + int((1-b_)*-60), 310 + k*80), txt, F_SUB, fill=col, alpha=a*b_)

def hudpanel(fr, t):
    a = ease((t-16.5)/0.4)*(1-ease((t-22.3)/0.3))
    if a <= 0: return
    T0 = 20.4
    dt = t - T0; sgn = "+" if dt >= 0 else "-"
    x0, y0 = 70, 250
    box_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(box_)
    bd.rounded_rectangle([x0, y0, x0+520, y0+170], radius=18, fill=(6, 8, 12, int(150*a)), outline=(255, 255, 255, int(60*a)), width=2)
    fr.alpha_composite(box_)
    shadow_text(fr, (x0+30, y0+22), f"T{sgn}00:{int(abs(dt)):02d}", F("InterDisplay-Black.otf", 64), fill=(255, 255, 255), alpha=a)
    st = "IGNITION" if 18.2 <= t < 20.4 else ("LIFTOFF" if t >= 20.4 else "FINAL COUNT")
    col = (255, 120, 100) if t < 20.4 else (120, 255, 170)
    shadow_text(fr, (x0+30, y0+110), "● " + st, F_TAG, fill=col, alpha=a*(1.0 if int(t*2.5) % 2 == 0 else 0.5))

def afterpanel(fr, t, m):
    a = ease((t-22.7)/0.4)*(1-ease((t-30.8)/0.3))
    if a <= 0: return
    tag(fr, "● TRACKING CAMERA", 22.6, 30.8, t)
    if m and t < 25.6: callout(fr, P(m, "fall"), "WHAT IS THIS?", a*ease((t-23.0)/0.4)*(1-ease((t-25.4)/0.3)), lx=90, ly=1250, col=GOLD)
    b_ = ease((t-25.9)/0.4)
    pop = 0.85 + 0.15*ease((t-25.9)/0.25)
    shadow_text(fr, (W//2, 300), "NOTHING WENT WRONG.", F("InterDisplay-Black.otf", int(76*pop)), anchor="ma", alpha=a*b_)
    shadow_text(fr, (W//2, 400), "IT'S NORMAL.", F("InterDisplay-Black.otf", int(84*pop)), fill=GOLD, anchor="ma", alpha=a*ease((t-28.4)/0.3))

_GRAD = None
def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(min(i, int(END3D*FPS)-1))
    brand(fr)
    intro(fr, t, m); closepanel(fr, t, m)
    for c in (7.0, 16.4, 22.5):
        if c <= t < c+0.15:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-c)/0.15)))))
    hudpanel(fr, t); afterpanel(fr, t, m)
    if t >= 22.5:
        global _GRAD
        if _GRAD is None:
            import numpy as _np
            g = _np.zeros((H, W, 4), _np.uint8); yy = _np.arange(H)[:, None]
            g[..., 3] = (_np.clip((yy - 1380)/260.0, 0, 1)*150).astype(_np.uint8)
            _GRAD = Image.fromarray(g, "RGBA")
        fr.alpha_composite(_GRAD)
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
    shadow_text(fr, (W//2, 360), "WHAT IS FALLING", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 455), "OFF THE ROCKET?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
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
