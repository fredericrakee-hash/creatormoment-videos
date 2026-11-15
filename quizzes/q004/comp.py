import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
NUM = 4
DUR = 54.0
CUTS = {"A": (0.0, 12.5), "B": (12.5, 22.0), "C": (22.0, 34.6)}
END3D = 34.6
BASE = QDIR
META = {}
for f in ("metaA.json", "metaB.json", "metaC.json"):
    META.update({int(k): v for k, v in json.load(open(f"{BASE}/{f}")).items()})
FD = "/usr/share/fonts/opentype/inter/"
def F(n, s): return ImageFont.truetype(FD+n, s)
F_TITLE = F("InterDisplay-Black.otf", 92)
F_SUB = F("Inter-SemiBold.otf", 52)
F_TAG = F("Inter-SemiBold.otf", 30)
F_LAB = F("Inter-SemiBold.otf", 30)
F_STAT = F("InterDisplay-Black.otf", 150)
F_Q = F("InterDisplay-Black.otf", 74)
F_OPT = F("InterDisplay-Black.otf", 64)
F_LET = F("InterDisplay-Black.otf", 60)
F_SMALL = F("Inter-SemiBold.otf", 38)
GOLD = (255, 200, 90)

def ease(x):
    x = max(0, min(1, x)); return x*x*(3-2*x)

SUBS = [(0.5, 5.3, "A jumbo jet, ready for a 12-hour flight. Full cabin. Full tanks."),
        (7.0, 8.9, "Full power\u2026 and up it goes."),
        (13.0, 17.1, "Minutes after takeoff, a warning goes off in the cockpit."),
        (19.9, 22.7, "The captain decides to turn back."),
        (23.0, 26.5, "And then\u2026 this. White trails pour out of both wings."),
        (26.8, 33.0, "Tons of fuel sprayed into the sky. On purpose. For 10\u201315 minutes.")]
OPTS = [("A", "To cool down the engines", 37.8), ("B", "To put out a fire", 40.0),
        ("C", "To mark their position for rescuers", 42.1), ("D", "To be light enough to land safely", 45.0)]
VOICE_END = 48.0

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
    return "C", int(round(CUTS["C"][0]*FPS))

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

def callout(fr, pt, label, a, lx=120, ly=1180):
    if a <= 0 or pt is None: return
    fx, fy, fz = pt
    if fz <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.line([(lx+260, ly-12), (fx, fy)], fill=GOLD+(int(230*a),), width=4)
    d.ellipse([fx-14, fy-14, fx+14, fy+14], outline=GOLD+(int(255*a),), width=4)
    fr.alpha_composite(lay)
    shadow_text(fr, (lx, ly), label, F_SMALL, fill=GOLD, alpha=a)

def xray_bulb(fr, m, a):
    """Dashed outline of the underwater nose seen through the water surface."""
    if a <= 0: return
    pts = [m["bulb_tip"], m["bulb_top"], m["bulb_back"], m["bulb_bot"]]
    if any(p[2] <= 0 for p in pts): return
    cx, cy = m["bulb_c"][0], m["bulb_c"][1]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    tip, top, back, bot = [(p[0], p[1]) for p in pts]
    # ellipse-ish closed curve through the four points
    poly = []
    for k in range(64):
        u = 2*math.pi*k/64
        c, s_ = math.cos(u), math.sin(u)
        fwd = tip if c >= 0 else back
        up = top if s_ >= 0 else bot
        x = cx + (fwd[0]-cx)*abs(c) + (up[0]-cx)*abs(s_)
        y = cy + (fwd[1]-cy)*abs(c) + (up[1]-cy)*abs(s_)
        poly.append((x, y))
    d.polygon(poly, fill=(255, 200, 90, int(45*a)))
    for k in range(0, 64, 2):
        d.line([poly[k], poly[(k+1) % 64]], fill=GOLD+(int(255*a),), width=5)
    fr.alpha_composite(lay)

def wave_panel(fr, t):
    """Animated explanation of wave interference."""
    a = ease((t-12.6)/0.5)*(1-ease((t-24.0)/0.5))
    if a <= 0: return
    x0, y0, x1, y1 = 70, 210, W-70, 820
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0, y0, x1, y1], radius=26, fill=(4, 10, 18, int(170*a)), outline=(255, 255, 255, int(70*a)), width=2)
    d.text((x0+34, y0+26), "WAVES AT THE FRONT OF THE SHIP", font=F_LAB, fill=(200, 205, 215, int(255*a)))
    show_red = ease((t-12.9)/0.6)
    show_blue = ease((t-16.6)/0.6)
    combine = ease((t-18.6)/1.2)
    rows = [(y0+190, "SHIP'S WAVE", (255, 95, 80), show_red*(1-0.55*combine), 0.0),
            (y0+345, "NOSE WAVE", (90, 190, 255), show_blue*(1-0.55*combine), math.pi)]
    ph = t*3.2
    def curve(yc, amp, phase, col, alpha, width=6):
        pts = []
        for k in range(160):
            x = x0+40 + (x1-x0-80)*k/159
            pts.append((x, yc - amp*math.sin(k/159*4*math.pi - ph + phase)))
        d.line(pts, fill=col+(int(255*alpha*a),), width=width, joint="curve")
    for yc, lab, col, al, phase in rows:
        if al > 0:
            d.text((x0+34, yc-95), lab, font=F_LAB, fill=col+(int(255*al*a),))
            curve(yc, 48, phase, col, al)
    if combine > 0:
        yc = y0+500
        d.text((x0+34, yc-80), "TOGETHER", font=F_LAB, fill=(110, 240, 150, int(255*combine*a)))
        curve(yc, 48*(1-combine) + 9*combine, 0.0, (110, 240, 150), combine, 7)
    fr.alpha_composite(lay)

def stat(fr, t):
    a = ease((t-23.9)/0.4)*(1-ease((t-27.4)/0.4))
    if a <= 0: return
    pop = 0.85 + 0.15*ease((t-23.9)/0.25)
    f = F("InterDisplay-Black.otf", int(150*pop))
    shadow_text(fr, (W//2, 380), "UP TO −15%", f, fill=(110, 240, 150), anchor="ma", alpha=a)
    shadow_text(fr, (W//2, 560), "FUEL", F_TITLE, anchor="ma", alpha=a)

def eicas(fr, t):
    a = ease((t-17.1)/0.3)*(1-ease((t-21.8)/0.4))
    if a <= 0: return
    x0, y0, s_ = W-430, 220, 370
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0, y0, x0+s_, y0+s_], radius=20, fill=(5, 7, 10, int(230*a)), outline=(90, 95, 105, int(255*a)), width=3)
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)
    mono_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 24)
    flash = int(t*3) % 2 == 0
    if flash: d.rounded_rectangle([x0+24, y0+22, x0+s_-24, y0+82], radius=8, fill=(220, 30, 25, int(255*a)))
    d.text((x0+s_//2, y0+52), "WARNING", font=mono, fill=(255, 255, 255, int(255*a)) if flash else (220, 40, 30, int(255*a)), anchor="mm")
    d.text((x0+30, y0+120), "ENG 3 FIRE", font=mono, fill=(255, 60, 50, int(255*a)))
    for k in range(4):
        cx = x0+60 + k*84; cy = y0+260
        col = (255, 60, 50) if k == 2 else (230, 230, 235)
        d.arc([cx-34, cy-34, cx+34, cy+34], 150, 390, fill=col+(int(255*a),), width=5)
        d.text((cx, cy+50), f"{k+1}", font=mono_s, fill=col+(int(255*a),), anchor="mm")
    fr.alpha_composite(lay)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META.get(i)
    brand(fr)
    if t < 6.2:
        a = ease((t-0.5)/0.4)*(1-ease((t-5.6)/0.5))
        shadow_text(fr, (60, 300), "FULL TANKS.", F_TITLE, alpha=a)
        shadow_text(fr, (60, 400), "12 HOURS", F_TITLE, alpha=a)
        shadow_text(fr, (60, 500), "TO GO.", F_TITLE, fill=GOLD, alpha=a)
    if 7.3 < t < 9.5:
        a = ease((t-7.35)/0.2)*(1-ease((t-9.1)/0.3))
        shadow_text(fr, (W//2, 330), "ROTATE", F_TITLE, fill=GOLD, anchor="ma", alpha=a)
    for c in (12.5, 22.0):
        if c <= t < c+0.15:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110*(1-(t-c)/0.15)))))
    eicas(fr, t)
    if 20.0 < t < 22.0:
        shadow_text(fr, (W//2, 700), "RETURNING TO THE AIRPORT", F_SMALL, fill=GOLD, anchor="ma", alpha=ease((t-20.0)/0.3)*(1-ease((t-21.7)/0.3)))
    if 24.6 < t < 33.0 and m:
        callout(fr, m.get("tipL"), "FUEL", ease((t-24.8)/0.4)*(1-ease((t-32.6)/0.4)), lx=110, ly=1250)
    for a_, b_, txt in SUBS:
        if a_ <= t < b_:
            d = ImageDraw.Draw(fr)
            for k, ln in enumerate(wrap(d, txt, F_SUB, W-140)):
                shadow_text(fr, (W//2, 1600 + k*64), ln, F_SUB, anchor="ma")
    if t > 34.0:
        fr = Image.blend(fr, quiz_bg(), ease((t-34.0)/0.6))
    return fr

_qbg = None
def quiz_bg():
    global _qbg
    if _qbg is None:
        last = frame3d(int(END3D*FPS)-2).convert("RGB")
        _qbg = Image.blend(last.filter(ImageFilter.GaussianBlur(26)), Image.new("RGB", (W, H), (6, 8, 14)), 0.62).convert("RGBA")
    return _qbg

F_OPT2 = F("InterDisplay-Black.otf", 46)
def quiz_frame(i):
    t = i/FPS
    fr = quiz_bg().copy(); brand(fr)
    qa = ease((t-34.6)/0.5)
    shadow_text(fr, (W//2, 300), "WHY WOULD PILOTS", F_Q, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 390), "DUMP TONS", F_Q, fill=GOLD, anchor="ma", alpha=qa)
    shadow_text(fr, (W//2, 480), "OF FUEL?", F_Q, fill=GOLD, anchor="ma", alpha=qa)
    for k, (L, txt, ts) in enumerate(OPTS):
        p = ease((t-ts+0.05)/0.35)
        if p <= 0: continue
        y = 640 + k*205; x0 = 70 + int((1-p)*-120); x1 = W-70 + int((1-p)*-120)
        speaking = ts <= t < ts + 2.0 and t < VOICE_END
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x0, y, x1, y+175], radius=28, fill=(255, 255, 255, int(30*p)),
                             outline=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(110*p)), width=4 if speaking else 2)
        ld.ellipse([x0+24, y+32, x0+134, y+142], fill=GOLD+(int(255*p),) if speaking else (255, 255, 255, int(235*p)))
        ld.text((x0+79, y+87), L, font=F_LET, fill=(8, 10, 16, int(255*p)), anchor="mm")
        lines = wrap(ld, txt, F_OPT2, x1-x0-200)
        for j, ln in enumerate(lines):
            ld.text((x0+165, y+87 + (j-(len(lines)-1)/2)*56), ln, font=F_OPT2, fill=(255, 255, 255, int(255*p)), anchor="lm")
        fr.alpha_composite(lay)
    if t > VOICE_END:
        a = ease((t-VOICE_END)/0.4)
        shadow_text(fr, (W//2, 1520), "COMMENT YOUR ANSWER \u2193", F_SUB, anchor="ma", alpha=a)
        shadow_text(fr, (W//2, 1600), "Solution in 2 days \u00b7 Follow so you don't miss it", F_SMALL, fill=(200, 205, 215), anchor="ma", alpha=a)
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
