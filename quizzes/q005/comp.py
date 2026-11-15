import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
NUM = 5
DUR = 45.4
CUTS = {"A": (0.0, 9.0), "B": (9.0, 29.6)}
END3D = 29.6
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

SUBS = [(0.3, 3.0, "Train wheels have a big problem."),
        (3.0, 8.85, "Both wheels sit on one solid steel axle – so they always turn at exactly the same speed."),
        (9.2, 14.3, "But in a curve, the outer rail is longer. The outer wheel has to travel further."),
        (14.5, 19.4, "So how does a train get around the bend without skidding? Watch the axle…"),
        (19.6, 21.7, "It slides a little bit outward."),
        (21.7, 26.4, "Now the outer wheel rolls on a bigger circle – the inner wheel on a smaller one."),
        (26.4, 29.3, "The train steers itself!")]
OPTS = [("A", "Hidden differential", 31.6), ("B", "Wheels slipping", 33.6), ("C", "Conical wheels", 36.0), ("D", "Banked track", 37.8)]
VOICE_END = 39.5

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
        _cache[i] = grade(Image.open(_src(i)), i, horizon_y=(900 if i < 270 else 5000))
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

def rails(fr, m, t):
    a = ease((t-10.4)/0.6)*(1-ease((t-14.0)/0.5))
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for key, col in (("railO", GOLD), ("railI", BLUE)):
        pts = [(p[0], p[1]) for p in m[key] if p[2] > 0.3]
        n = max(2, int(len(pts)*ease((t-10.4)/1.2)))
        if len(pts) > 1:
            d.line(pts[:n], fill=col+(int(235*a),), width=9, joint="curve")
    fr.alpha_composite(lay)
    shadow_text(fr, (70, 300), "OUTER RAIL", F_TITLE, fill=GOLD, alpha=a)
    shadow_text(fr, (70, 400), "= LONGER", F_TITLE, alpha=a)
    shadow_text(fr, (70, 520), "INNER RAIL = SHORTER", F_LAB, fill=BLUE, alpha=a*ease((t-11.2)/0.5))

def slide(fr, m, t):
    a = ease((t-19.7)/0.4)*(1-ease((t-22.0)/0.4))
    if a <= 0: return
    ax = m["axle"]; co = m["cO"]
    dx, dy = co[0]-m["cI"][0], co[1]-m["cI"][1]; L = math.hypot(dx, dy) or 1; ux, uy = dx/L, dy/L
    y = ax[1] - 230
    x0 = ax[0] + 120*ux; x1 = ax[0] - 140*ux + ux*0  # arrow points toward the outer side
    x1 = ax[0] + 120*ux - 300*abs(ux)*(1 if ux < 0 else -1)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sx, ex = ax[0] + 150, ax[0] - 150
    if co[0] > ax[0]: sx, ex = ex, sx
    d.line([(sx, y), (ex, y)], fill=GOLD+(int(255*a),), width=10)
    hd = -1 if ex < sx else 1
    d.polygon([(ex + hd*36, y), (ex - hd*6, y-30), (ex - hd*6, y+30)], fill=GOLD+(int(255*a),))
    fr.alpha_composite(lay)
    shadow_text(fr, (W//2, y-110), "SLIDES OUTWARD", F_SMALL, fill=GOLD, anchor="ma", alpha=a)

def circles(fr, m, t):
    a = ease((t-21.9)/0.5)*(1-ease((t-29.0)/0.5))
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for key, top, col, k, lab, delay in (("cO", "topO", GOLD, 1.0, "BIGGER CIRCLE", 0.0), ("cI", "topI", BLUE, 0.86, "SMALLER CIRCLE", 1.3)):
        b = a*ease((t-21.9-delay)/0.5)
        if b <= 0: continue
        c = m[key]; tp = m[top]
        r = math.hypot(tp[0]-c[0], tp[1]-c[1])*k
        rx = r*0.42                                    # wheel is seen almost edge-on: draw the rolling circle as a tall ellipse
        d.ellipse([c[0]-rx, c[1]-r, c[0]+rx, c[1]+r], outline=col+(int(255*b),), width=7)
        # spin marker
        an = (t-21.9)*4.0*(1 if key == "cO" else 0.86)
        d.ellipse([c[0]+rx*math.sin(an)-11, c[1]-r*math.cos(an)-11, c[0]+rx*math.sin(an)+11, c[1]-r*math.cos(an)+11], fill=col+(int(255*b),))
    fr.alpha_composite(lay)
    shadow_text(fr, (W//2, 300), "OUTER WHEEL:", F_LAB, fill=(220, 220, 225), anchor="ma", alpha=a)
    shadow_text(fr, (W//2, 350), "BIGGER CIRCLE", F_TITLE, fill=GOLD, anchor="ma", alpha=a)
    b = a*ease((t-23.2)/0.5)
    shadow_text(fr, (W//2, 500), "INNER WHEEL:", F_LAB, fill=(220, 220, 225), anchor="ma", alpha=b)
    shadow_text(fr, (W//2, 550), "SMALLER CIRCLE", F_TITLE, fill=BLUE, anchor="ma", alpha=b)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(i)
    brand(fr)
    if t < 8.6:
        a = ease((t-0.3)/0.4)*(1-ease((t-8.1)/0.5))
        shadow_text(fr, (60, 300), "ONE SOLID AXLE.", F_TITLE, alpha=a)
        shadow_text(fr, (60, 400), "TWO WHEELS.", F_TITLE, alpha=a*ease((t-3.2)/0.4))
        shadow_text(fr, (60, 500), "ONE PROBLEM.", F_TITLE, fill=GOLD, alpha=a*ease((t-5.0)/0.4))
    if 9.0 <= t < 9.15:
        fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-9.0)/0.15)))))
    if m:
        rails(fr, m, t)
        if 15.6 < t < 19.6:
            callout(fr, m.get("axle"), "WATCH THE AXLE", ease((t-15.8)/0.4)*(1-ease((t-19.2)/0.3)), lx=110, ly=520)
        slide(fr, m, t)
        circles(fr, m, t)
    for a_, b_, txt in SUBS:
        if a_ <= t < b_:
            d = ImageDraw.Draw(fr)
            for k, ln in enumerate(wrap(d, txt, F_SUB, W-140)):
                shadow_text(fr, (W//2, 1560 + k*64), ln, F_SUB, anchor="ma")
    if t > 29.0:
        fr = Image.blend(fr, quiz_bg(), ease((t-29.0)/0.6))
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
    qa = ease((t-29.6)/0.5)
    shadow_text(fr, (W//2, 360), "WHAT MAKES", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 455), "THIS WORK?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
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
