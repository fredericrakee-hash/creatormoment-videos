import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
NUM = 6
DUR = 43.5
CUTS = {"A": (0.0, 7.6), "B": (7.6, 27.0)}
END3D = 27.0
BASE = QDIR
META = {}
for f in ("metaB.json",):
    META.update({int(k): v for k, v in json.load(open(f"{BASE}/{f}")).items()})
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

SUBS = [(0.3, 3.6, "This tank is racing over rough ground at full speed."),
        (3.6, 7.35, "The hull is bouncing up and down like a boat in a storm."),
        (7.8, 10.3, "But look at the long barrel."),
        (10.3, 13.95, "It stays locked on the target – no matter how hard the tank pitches."),
        (14.3, 17.8, "Sensors feel every single bump…"),
        (17.8, 21.95, "…and powerful motors move the barrel the opposite way, many times every second."),
        (22.3, 26.55, "That's how a modern tank can hit a target while it's still driving.")]
OPTS = [("A", "Active suspension", 29.4), ("B", "Gun stabilizer", 31.4), ("C", "Muzzle brake", 33.4), ("D", "Laser rangefinder", 35.1)]
VOICE_END = 37.6

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

def hud(fr, m, t):
    a = ease((t-8.6)/0.5)*(1-ease((t-26.6)/0.4))
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    mz, fa = m["muz"], m["far"]
    if mz[2] > 0 and fa[2] > 0:
        dx, dy = fa[0]-mz[0], fa[1]-mz[1]; L = math.hypot(dx, dy) or 1
        for k in range(0, 900, 36):
            p0 = (mz[0]+dx/L*k, mz[1]+dy/L*k); p1 = (mz[0]+dx/L*(k+20), mz[1]+dy/L*(k+20))
            d.line([p0, p1], fill=(120, 255, 160, int(220*a)), width=5)
        d.ellipse([mz[0]-12, mz[1]-12, mz[0]+12, mz[1]+12], outline=(120, 255, 160, int(255*a)), width=4)
    hf, hr = m["hf"], m["hr"]
    if hf[2] > 0 and hr[2] > 0:
        d.line([(hr[0], hr[1]), (hf[0], hf[1])], fill=GOLD+(int(200*a),), width=5)
    fr.alpha_composite(lay)
    # readouts
    x0, y0 = 70, 260
    box_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(box_)
    bd.rounded_rectangle([x0, y0, x0+520, y0+210], radius=18, fill=(4, 10, 8, int(150*a)), outline=(255, 255, 255, int(60*a)), width=2)
    fr.alpha_composite(box_)
    p = m["pitch"]
    shadow_text(fr, (x0+30, y0+28), "HULL ANGLE", F_TAG, fill=(220, 220, 225), alpha=a)
    shadow_text(fr, (x0+300, y0+16), f"{p:+.1f}°", F_LAB, fill=GOLD, alpha=a)
    shadow_text(fr, (x0+30, y0+88), "BARREL ANGLE", F_TAG, fill=(220, 220, 225), alpha=a)
    shadow_text(fr, (x0+300, y0+76), "+0.6°", F_LAB, fill=(120, 255, 160), alpha=a)
    blink = 1.0 if int(t*2.5) % 2 == 0 else 0.55
    shadow_text(fr, (x0+30, y0+148), "● ON TARGET", F_TAG, fill=(120, 255, 160), alpha=a*blink)

def stat(fr, t):
    a = ease((t-22.4)/0.4)*(1-ease((t-26.5)/0.4))
    if a <= 0: return
    pop = 0.85 + 0.15*ease((t-22.4)/0.25)
    f = F("InterDisplay-Black.otf", int(118*pop))
    shadow_text(fr, (W//2, 560), "HITS WHILE", f, fill=(120, 255, 160), anchor="ma", alpha=a)
    shadow_text(fr, (W//2, 690), "DRIVING", F_TITLE, anchor="ma", alpha=a)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(i)
    brand(fr)
    if t < 7.4:
        a = ease((t-0.3)/0.4)*(1-ease((t-6.9)/0.5))
        shadow_text(fr, (60, 300), "FULL SPEED.", F_TITLE, alpha=a)
        shadow_text(fr, (60, 400), "ROUGH GROUND.", F_TITLE, alpha=a*ease((t-1.8)/0.4))
        shadow_text(fr, (60, 500), "WATCH CLOSELY.", F_TITLE, fill=GOLD, alpha=a*ease((t-4.0)/0.4))
    if 7.6 <= t < 7.75:
        fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-7.6)/0.15)))))
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
    t = i/FPS
    fr = quiz_bg().copy(); brand(fr)
    qa = ease((t-27.0)/0.5)
    shadow_text(fr, (W//2, 360), "WHAT IS THIS", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 455), "SYSTEM CALLED?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
    for k, (L, txt, ts) in enumerate(OPTS):
        p = ease((t-ts+0.05)/0.35)
        if p <= 0: continue
        y = 680 + k*200; x0 = 90 + int((1-p)*-120); x1 = W-90 + int((1-p)*-120)
        speaking = ts <= t < ts + 1.6 and t < VOICE_END
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x0, y, x1, y+160], radius=28, fill=(255, 255, 255, int(30*p)),
                             outline=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(110*p)), width=4 if speaking else 2)
        ld.ellipse([x0+26, y+24, x0+138, y+136], fill=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(235*p)))
        ld.text((x0+82, y+80), L, font=F_LET, fill=(8, 10, 16, int(255*p)), anchor="mm")
        ld.text((x0+170, y+80), txt, font=F_OPT, fill=(255, 255, 255, int(255*p)), anchor="lm")
        fr.alpha_composite(lay)
    if t > VOICE_END:
        a = ease((t-VOICE_END)/0.4)
        shadow_text(fr, (W//2, 1520), "COMMENT YOUR ANSWER ↓", F_SUB, anchor="ma", alpha=a)
        shadow_text(fr, (W//2, 1600), "Solution in 2 days · Follow so you don't miss it", F_SMALL, fill=(200, 205, 215), anchor="ma", alpha=a)
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
