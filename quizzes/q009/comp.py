import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
NUM = 9
DUR = 49.0
CUTS = {"A": (0.0, 7.8), "B": (7.8, 17.9), "C": (17.9, 29.2)}
END3D = 29.2
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

SUBS = [(0.3, 3.6, "This fighter jet is coming in to land on an aircraft carrier…"),
        (3.6, 7.5, "…at around 250 kilometers per hour."),
        (8.0, 10.5, "The runway is tiny – and it's moving."),
        (10.5, 14.8, "So a hook under the tail grabs one of the steel cables across the deck…"),
        (14.8, 17.9, "…and stops the jet in about two seconds."),
        (18.2, 19.7, "But watch the engines."),
        (19.7, 25.3, "The moment the wheels slam onto the deck, the pilot pushes the throttle to full power."),
        (25.6, 28.8, "Full power – at the exact moment you want to stop.")]
OPTS = [("A", "To pull the cable tighter", 31.6), ("B", "To keep the engines from dying", 33.9), ("C", "To steer straight on the deck", 36.7), ("D", "In case it has to take off again", 39.0)]
VOICE_END = 42.3
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
    return "B", int(round(CUTS["B"][0]*FPS))

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
        _cache[i] = grade(Image.open(_src(i)), i, horizon_y=5000)
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

def disp_kmh(m, t):
    if t < 21.0: return 250
    return int(round(250*min(1.0, m["kmh"]/234.0)))

def hud(fr, m, t):
    a = ease((t-19.0)/0.5)*(1-ease((t-25.2)/0.4))
    if a <= 0: return
    x0, y0 = 70, 250
    box_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(box_)
    bd.rounded_rectangle([x0, y0, x0+560, y0+230], radius=18, fill=(6, 8, 12, int(150*a)), outline=(255, 255, 255, int(60*a)), width=2)
    thr = m["thr"]; full = thr > 0.97
    col = RED if full else GOLD
    bx0, by0, bx1 = x0+30, y0+150, x0+530
    bd.rounded_rectangle([bx0, by0, bx1, by0+36], radius=8, fill=(255, 255, 255, int(28*a)), outline=(255, 255, 255, int(80*a)), width=2)
    bd.rounded_rectangle([bx0+4, by0+4, bx0+4+int((bx1-bx0-8)*thr), by0+32], radius=6, fill=col+(int(230*a),))
    fr.alpha_composite(box_)
    shadow_text(fr, (x0+30, y0+28), "THROTTLE", F_TAG, fill=(220, 220, 225), alpha=a)
    blink = 1.0 if (not full or int(t*3) % 2 == 0) else 0.6
    shadow_text(fr, (x0+300, y0+16), f"{int(round(thr*100))}%" + ("  MAX" if full else ""), F_LAB, fill=col, alpha=a*blink)
    shadow_text(fr, (x0+30, y0+88), "SPEED", F_TAG, fill=(220, 220, 225), alpha=a)
    shadow_text(fr, (x0+300, y0+76), f"{disp_kmh(m, t)} km/h", F_LAB, fill=(255, 255, 255), alpha=a)
    # glow marker on the nozzles
    n = m["noz"]
    if 20.9 < t < 26.0 and n[2] > 0:
        aa = a*ease((t-20.9)/0.3)*(1-ease((t-25.6)/0.4))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        r = 52 + 6*math.sin(t*12)
        d.ellipse([n[0]-r, n[1]-r, n[0]+r, n[1]+r], outline=RED+(int(255*aa),), width=5)
        fr.alpha_composite(lay)
        shadow_text(fr, (n[0], n[1]-r-58), "ENGINES", F_TAG, fill=RED, anchor="ma", alpha=aa)

def tag_jet(fr, m, t):
    a = ease((t-1.0)/0.5)*(1-ease((t-7.3)/0.4))
    if a <= 0: return
    j = m["jet"]
    if j[2] <= 0: return
    x, y = j[0]+40, j[1]-170
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.line([(j[0], j[1]-30), (x, y+70)], fill=(255, 255, 255, int(180*a)), width=3)
    d.rounded_rectangle([x, y, x+330, y+70], radius=10, fill=(6, 8, 12, int(150*a)), outline=(255, 255, 255, int(90*a)), width=2)
    fr.alpha_composite(lay)
    shadow_text(fr, (x+20, y+18), "FINAL APPROACH · 250 km/h", F_TAG, fill=(220, 235, 255), alpha=a)

def stat(fr, t):
    a = ease((t-25.6)/0.4)*(1-ease((t-28.7)/0.4))
    if a <= 0: return
    pop = 0.85 + 0.15*ease((t-25.6)/0.25)
    f = F("InterDisplay-Black.otf", int(118*pop))
    shadow_text(fr, (W//2, 560), "FULL POWER", f, fill=RED, anchor="ma", alpha=a)
    shadow_text(fr, (W//2, 690), "TO STOP?!", F_TITLE, anchor="ma", alpha=a)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(min(i, int(END3D*FPS)-1))
    brand(fr)
    if t < 7.6:
        a = ease((t-0.3)/0.4)*(1-ease((t-7.2)/0.5))
        shadow_text(fr, (60, 300), "250 KM/H.", F_TITLE, alpha=a)
        shadow_text(fr, (60, 400), "TINY RUNWAY.", F_TITLE, alpha=a*ease((t-2.4)/0.4))
        shadow_text(fr, (60, 500), "WATCH CLOSELY.", F_TITLE, fill=GOLD, alpha=a*ease((t-4.6)/0.4))
        if m: tag_jet(fr, m, t)
    for c in (7.8, 17.9):
        if c <= t < c+0.15:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-c)/0.15)))))
    if m and 10.6 <= t < 17.6:
        a = ease((t-10.6)/0.4)*(1-ease((t-17.2)/0.4))
        callout(fr, m["wire0"], "ARRESTING CABLES", a, lx=90, ly=1180, col=GOLD)
        if m["hook"][2] > 0 and t > 11.6:
            callout(fr, m["hook"], "TAILHOOK", a*ease((t-11.6)/0.4), lx=600, ly=460, col=BLUE)
    if m:
        hud(fr, m, t)
    stat(fr, t)
    for a_, b_, txt in SUBS:
        if a_ <= t < b_:
            d = ImageDraw.Draw(fr)
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
    shadow_text(fr, (W//2, 360), "WHY FULL POWER", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 455), "WHILE LANDING?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
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
