import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
DUR = 44.2
CUT = 19.0          # shot A -> shot B
END3D = 29.0
NUM = 2
BASE = QDIR
META = {}
for f in ("metaA.json", "metaB.json"):
    META.update({int(k): v for k, v in json.load(open(f"{BASE}/{f}")).items()})
FD = "/usr/share/fonts/opentype/inter/"
def F(n, s): return ImageFont.truetype(FD+n, s)
F_TITLE = F("InterDisplay-Black.otf", 96)
F_SUB = F("Inter-SemiBold.otf", 52)
F_TAG = F("Inter-SemiBold.otf", 30)
F_TEL_L = F("Inter-SemiBold.otf", 24)
F_TEL_V = F("InterDisplay-Black.otf", 52)
F_Q = F("InterDisplay-Black.otf", 74)
F_OPT = F("InterDisplay-Black.otf", 64)
F_LET = F("InterDisplay-Black.otf", 60)
F_SMALL = F("Inter-SemiBold.otf", 38)

def ease(x):
    x = max(0, min(1, x)); return x*x*(3-2*x)

SUBS = [(0.3, 7.9, "Back from space. Coming down tail first."),
        (8.2, 13.2, "Four metal grids unfold – glowing from the heat."),
        (13.5, 18.4, "They steer the booster. No pilot on board."),
        (19.4, 22.7, "Seconds before impact, the engine fires again."),
        (23.0, 26.9, "Legs out. Touchdown – on a ship, mid-ocean.")]
OPTS = [("A", "Canards", 31.6), ("B", "Air brakes", 33.1), ("C", "Grid fins", 34.8), ("D", "Ailerons", 36.4)]
VOICE_END = 38.2

def shadow_text(base, xy, txt, font, fill=(255, 255, 255), blur=6, sh=170, anchor="la"):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((xy[0]+2, xy[1]+3), txt, font=font, fill=(0, 0, 0, sh), anchor=anchor)
    lay = lay.filter(ImageFilter.GaussianBlur(blur)); base.alpha_composite(lay)
    ImageDraw.Draw(base).text(xy, txt, font=font, fill=fill, anchor=anchor)

_cache = {}
CUTF = int(CUT*FPS)
def frame3d(i):
    def load(k):
        k = max(0, min(k, int(END3D*FPS)-1)); k -= k % 2
        while k >= 0 and not os.path.exists(f"{BASE}/frames/f{k:04d}.png"): k -= 2
        if k < 0: return Image.new("RGB", (W, H), (40, 60, 90))
        if k not in _cache:
            if len(_cache) > 4: _cache.clear()
            _cache[k] = grade(Image.open(f"{BASE}/frames/f{k:04d}.png"), k//2, horizon_y=5000)
        return _cache[k]
    if i % 2 == 0: return load(i)
    if i+1 >= CUTF > i: return load(i-1)          # never blend across the cut
    return Image.blend(load(i-1), load(i+1), 0.5)

def brand(fr):
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([56, 112, 262, 166], radius=12, fill=(0, 0, 0, 120), outline=(255, 255, 255, 90), width=2)
    d.text((159, 139), f"QUIZ #{NUM}", font=F_TAG, fill=(255, 255, 255), anchor="mm")

def telemetry(fr, i):
    """Webcast-style telemetry for the first stage (bottom area, above captions)."""
    t = i/FPS
    if t < CUT:
        alt_km = 55 - 17*(t/CUT); spd = 4800 - 900*(t/CUT)
    else:
        m0, m1 = META.get(i, META[max(META)]), META.get(min(i+2, max(META)), META[max(META)])
        alt_km = max(0.0, (m0["alt"]-3.0)/1000.0)
        spd = max(0.0, (m0["alt"]-m1["alt"])/(2/FPS)*3.6)
        if t > 25.6: spd = 0.0
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y = 1430 if t < CUT else 196
    d.rounded_rectangle([60, y, W-60, y+120], radius=18, fill=(0, 0, 0, 105), outline=(255, 255, 255, 60), width=2)
    d.text((95, y+16), "STAGE 1", font=F_TEL_L, fill=(255, 255, 255, 200))
    d.text((95, y+48), "SPEED", font=F_TEL_L, fill=(180, 185, 195, 230))
    d.text((210, y+36), f"{spd:,.0f}", font=F_TEL_V, fill=(255, 255, 255, 255))
    d.text((210 + d.textlength(f"{spd:,.0f}", font=F_TEL_V) + 10, y+60), "KM/H", font=F_TEL_L, fill=(180, 185, 195, 230))
    d.text((600, y+48), "ALTITUDE", font=F_TEL_L, fill=(180, 185, 195, 230))
    av = f"{alt_km:.1f}" if alt_km >= 1 else f"{alt_km:.2f}"
    d.text((745, y+36), av, font=F_TEL_V, fill=(255, 255, 255, 255))
    d.text((745 + d.textlength(av, font=F_TEL_V) + 10, y+60), "KM", font=F_TEL_L, fill=(180, 185, 195, 230))
    fr.alpha_composite(lay)

def pointer(fr, i, t):
    """'WHAT ARE THESE?' callout pointing at a grid fin while they deploy."""
    a = ease((t-9.4)/0.5)*(1-ease((t-13.0)/0.5))
    if a <= 0: return
    fx, fy, fz = META[i]["fin"]
    if fz <= 0: return
    lx, ly = 140, 760
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.line([(lx+330, ly+28), (fx, fy)], fill=(255, 200, 90, int(230*a)), width=4)
    d.ellipse([fx-12, fy-12, fx+12, fy+12], outline=(255, 200, 90, int(255*a)), width=4)
    fr.alpha_composite(lay)
    lay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_text(lay2, (lx, ly), "WHAT ARE THESE?", F_SMALL, fill=(255, 200, 90))
    lay2.putalpha(lay2.split()[3].point(lambda v: int(v*a))); fr.alpha_composite(lay2)

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    if t < 26.9: telemetry(fr, i)
    pointer(fr, i, t)
    brand(fr)
    if t < 7.6:
        a = ease((t-0.2)/0.4)*(1-ease((t-7.0)/0.5))
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow_text(lay, (60, 330), "BACK FROM", F_TITLE)
            shadow_text(lay, (60, 430), "SPACE.", F_TITLE, fill=(255, 200, 90))
            lay.putalpha(lay.split()[3].point(lambda v: int(v*a))); fr.alpha_composite(lay)
    # quick flash at the cut
    if CUT <= t < CUT+0.15:
        fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(120*(1-(t-CUT)/0.15)))))
    for a_, b_, txt in SUBS:
        if a_ <= t < b_:
            d = ImageDraw.Draw(fr); lines, cur = [], ""
            for w_ in txt.split():
                tt_ = (cur+" "+w_).strip()
                if d.textlength(tt_, font=F_SUB) > W-140 and cur: lines.append(cur); cur = w_
                else: cur = tt_
            lines.append(cur)
            for k_, ln in enumerate(lines):
                shadow_text(fr, (W//2, 1610 + k_*64), ln, F_SUB, anchor="ma")
    if t > 28.4:
        fr = Image.blend(fr, quiz_bg(), ease((t-28.4)/0.6))
    return fr

_qbg = None
def quiz_bg():
    global _qbg
    if _qbg is None:
        last = frame3d(int(END3D*FPS)-2).convert("RGB")
        b = last.filter(ImageFilter.GaussianBlur(26))
        _qbg = Image.blend(b, Image.new("RGB", (W, H), (6, 8, 14)), 0.62).convert("RGBA")
    return _qbg

def quiz_frame(i):
    t = i/FPS
    fr = quiz_bg().copy(); brand(fr)
    qa = ease((t-29.0)/0.5)
    if qa > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow_text(lay, (W//2, 330), "WHAT ARE THESE", F_Q, anchor="ma")
        shadow_text(lay, (W//2, 420), "GRIDS CALLED?", F_Q, fill=(255, 200, 90), anchor="ma")
        lay.putalpha(lay.split()[3].point(lambda v: int(v*qa))); fr.alpha_composite(lay)
    for k, (L, txt, ts) in enumerate(OPTS):
        p = ease((t-ts+0.05)/0.35)
        if p <= 0: continue
        y = 620 + k*200; x0 = 90 + int((1-p)*-120); x1 = W-90 + int((1-p)*-120)
        speaking = ts <= t < ts + 1.4 and t < VOICE_END
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x0, y, x1, y+160], radius=28, fill=(255, 255, 255, int(30*p)),
                             outline=(255, 200, 90, int(255*p)) if speaking else (255, 255, 255, int(110*p)), width=4 if speaking else 2)
        ld.ellipse([x0+26, y+24, x0+138, y+136], fill=(255, 200, 90, int(255*p)) if speaking else (255, 255, 255, int(235*p)))
        ld.text((x0+82, y+80), L, font=F_LET, fill=(8, 10, 16, int(255*p)), anchor="mm")
        ld.text((x0+180, y+80), txt, font=F_OPT, fill=(255, 255, 255, int(255*p)), anchor="lm")
        fr.alpha_composite(lay)
    if t > VOICE_END:
        a = ease((t-VOICE_END)/0.4)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow_text(lay, (W//2, 1480), "COMMENT YOUR ANSWER ↓", F_SUB, anchor="ma")
        shadow_text(lay, (W//2, 1560), "Solution in 2 days · Follow so you don't miss it", F_SMALL, fill=(200, 205, 215), anchor="ma")
        lay.putalpha(lay.split()[3].point(lambda v: int(v*a))); fr.alpha_composite(lay)
    return fr

def draw(i):
    t = i/FPS
    return (scene_frame(i) if t < END3D else quiz_frame(i)).convert("RGB")

def clean_clip(out, t0, t1):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
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
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                          "-pix_fmt", "yuv420p", sys.argv[1]], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)): p.stdin.write(draw(i).tobytes())
    p.stdin.close(); sys.exit(p.wait())
