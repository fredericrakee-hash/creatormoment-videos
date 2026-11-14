import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from grade import grade

W, H, FPS = 1080, 1920, 30
DUR = 43.0
END3D = 27.2
BASE = ""+QDIR+""
META = {int(k): v for k, v in json.load(open(f"{BASE}/meta.json")).items()}
FD = "/usr/share/fonts/opentype/inter/"
def F(n, s): return ImageFont.truetype(FD+n, s)
F_TITLE = F("InterDisplay-Black.otf", 96)
F_SUB = F("Inter-SemiBold.otf", 52)
F_TAG = F("Inter-SemiBold.otf", 30)
F_MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 30)
F_MONO_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 24)
F_Q = F("InterDisplay-Black.otf", 74)
F_OPT = F("InterDisplay-Black.otf", 64)
F_LET = F("InterDisplay-Black.otf", 60)
F_SMALL = F("Inter-SemiBold.otf", 38)

def ease(x):
    x = max(0, min(1, x)); return x*x*(3-2*x)

SUBS = [(0.3, 4.2, "Two planes. Same altitude."),
        (6.2, 11.2, "Nobody panics. A hidden system just kicked in."),
        (11.5, 15.4, "The planes talk to each other…"),
        (19.3, 22.6, "One climbs. One descends."),
        (22.9, 26.6, "Hundreds of feet apart. Safe.")]
OPTS = [("A", "GPWS", 30.2), ("B", "TCAS", 32.3), ("C", "ILS", 33.8), ("D", "ATIS", 35.5)]

def shadow_text(base, xy, txt, font, fill=(255, 255, 255), blur=6, sh=170, anchor="la"):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((xy[0]+2, xy[1]+3), txt, font=font, fill=(0, 0, 0, sh), anchor=anchor)
    lay = lay.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(lay)
    ImageDraw.Draw(base).text(xy, txt, font=font, fill=fill, anchor=anchor)

_cache = {}
def frame3d(i):
    def load(k):
        k = max(0, min(k, int(END3D*FPS)-1)); k -= k % 2
        while k >= 0 and not os.path.exists(f"{BASE}/frames/f{k:04d}.png"): k -= 2
        if k < 0: return Image.new("RGB", (W, H), (40, 60, 90))
        if k not in _cache:
            if len(_cache) > 4: _cache.clear()
            _cache[k] = grade(Image.open(f"{BASE}/frames/f{k:04d}.png"), k//2)
        return _cache[k]
    if i % 2 == 0: return load(i)
    return Image.blend(load(i-1), load(i+1), 0.5)

def fl(t, side):
    z = (34*ease((t-15.8)/4.2)) if side == "L" else (-34*ease((t-17.3)/4.2))
    return 350 + round(z*0.35)       # cosmetic: displayed flight level change

def datatag(fr, x, y, call, t, side, col=(120, 255, 170)):
    d = ImageDraw.Draw(fr)
    ox, oy = (x - 40, y - 150) if side == "L" else (x + 40, y - 150)
    ox = max(110, min(W-110, ox))
    d.line([(x, y-30), (ox, oy+60)], fill=col+(200,), width=3)
    lvl = fl(t, side)
    trend = ""
    if side == "L" and t > 15.8: trend = " ↑"
    if side == "R" and t > 17.3: trend = " ↓"
    lines = [call, f"FL{lvl}{trend}"]
    for k, ln in enumerate(lines):
        shadow_text(fr, (ox, oy + k*34), ln, F_MONO, fill=col, blur=3, sh=200, anchor="ma")

def tcas_display(fr, t):
    # Navigation-display style TCAS inset, top-right
    x0, y0, s = W-380, 210, 330
    a = ease((t-4.2)/0.4) * (1 - ease((t-22.6)/0.4))
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0, y0, x0+s, y0+s], radius=22, fill=(5, 7, 10, int(225*a)), outline=(90, 95, 105, int(255*a)), width=3)
    cx, cy = x0 + s/2, y0 + s*0.72
    r = s*0.42
    # range arcs (dashed)
    for ang in range(200, 341, 12):
        a1 = math.radians(ang); a2 = math.radians(ang+6)
        d.arc([cx-r, cy-r, cx+r, cy+r], ang, ang+6, fill=(200, 200, 210, int(200*a)), width=2)
    for ang in range(0, 360, 30):
        px, py = cx + r*0.5*math.cos(math.radians(ang)), cy + r*0.5*math.sin(math.radians(ang))
        d.ellipse([px-2, py-2, px+2, py+2], fill=(200, 200, 210, int(220*a)))
    # own aircraft symbol
    d.polygon([(cx, cy-16), (cx-14, cy+12), (cx, cy+5), (cx+14, cy+12)], fill=(255, 255, 255, int(255*a)))
    # intruder approaching from ahead
    prog = min(1, t/24.5)
    iy = cy - r*1.05*(1-prog) - 10
    ix = cx + 4
    if t < 15.6:
        col = (255, 176, 0)      # traffic advisory: amber circle
        d.ellipse([ix-12, iy-12, ix+12, iy+12], fill=col+(int(255*a),))
    else:
        col = (255, 40, 30)      # resolution advisory: red square
        d.rectangle([ix-12, iy-12, ix+12, iy+12], fill=col+(int(255*a),))
    rel = fl(t, "R") - fl(t, "L")
    d.text((ix+18, iy-26), f"{rel:+03d}" if rel else "00", font=F_MONO_S, fill=col+(int(255*a),))
    # header message
    msg, mcol = "TCAS", (140, 145, 155)
    if 4.4 < t < 7.0: msg, mcol = "TRAFFIC", (255, 176, 0)
    if 15.6 < t < 22.6: msg, mcol = "CLIMB", (255, 40, 30)
    if 15.6 < t < 22.6 and int(t*3) % 2 == 1 and t < 17.5: msg = ""
    if msg: d.text((x0+22, y0+18), msg, font=F_MONO, fill=mcol+(int(255*a),))
    d.text((x0+s-22, y0+18), "TA/RA", font=F_MONO_S, fill=(140, 145, 155, int(255*a)), anchor="ra")
    fr.alpha_composite(lay)

def brand(fr):
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([56, 112, 262, 166], radius=12, fill=(0, 0, 0, 120), outline=(255, 255, 255, 90), width=2)
    d.text((159, 139), "QUIZ #1", font=F_TAG, fill=(255, 255, 255), anchor="mm")

def scene_frame(i):
    t = i/FPS
    fr = frame3d(i).convert("RGBA")
    m = META[min(i, max(META))]
    (lx, ly), (rx, ry) = m["L"], m["R"]
    if 0.3 < t < 23.5:
        datatag(fr, lx, ly, "CMA214", t, "L")
        datatag(fr, rx, ry, "VSP088", t, "R", col=(255, 215, 120))
    tcas_display(fr, t)
    brand(fr)
    if t < 6.0:
        a = ease((t-0.2)/0.4)*(1-ease((t-5.4)/0.5))
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow_text(lay, (W//2 - 0 if False else 60, 600), "COLLISION", F_TITLE, fill=(255, 255, 255))
            shadow_text(lay, (60, 700), "COURSE.", F_TITLE, fill=(255, 92, 70))
            al = lay.split()[3].point(lambda v: int(v*a)); lay.putalpha(al); fr.alpha_composite(lay)
    for a_, b_, txt in SUBS:
        if a_ <= t < b_:
            shadow_text(fr, (W//2, 1640), txt, F_SUB, anchor="ma")
    if t > 26.6:
        k = ease((t-26.6)/0.6)
        fr = Image.blend(fr, quiz_bg(), k)
    return fr

_qbg = None
def quiz_bg():
    global _qbg
    if _qbg is None:
        last = frame3d(int(END3D*FPS)-2).convert("RGB")
        b = last.filter(ImageFilter.GaussianBlur(26))
        dark = Image.new("RGB", (W, H), (6, 8, 14))
        _qbg = Image.blend(b, dark, 0.62).convert("RGBA")
    return _qbg

def quiz_frame(i):
    t = i/FPS
    fr = quiz_bg().copy(); brand(fr)
    d = ImageDraw.Draw(fr)
    qa = ease((t-27.2)/0.5)
    if qa > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow_text(lay, (W//2, 330), "WHAT IS THIS", F_Q, anchor="ma")
        shadow_text(lay, (W//2, 420), "SYSTEM CALLED?", F_Q, fill=(255, 200, 90), anchor="ma")
        lay.putalpha(lay.split()[3].point(lambda v: int(v*qa))); fr.alpha_composite(lay)
    d = ImageDraw.Draw(fr)
    for k, (L, txt, ts) in enumerate(OPTS):
        p = ease((t-ts+0.05)/0.35)
        if p <= 0: continue
        y = 620 + k*200; x0 = 90 + int((1-p)*-120); x1 = W-90 + int((1-p)*-120)
        speaking = ts <= t < ts + 1.6 and t < 37.0
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x0, y, x1, y+160], radius=28, fill=(255, 255, 255, int(30*p)),
                             outline=(255, 200, 90, int(255*p)) if speaking else (255, 255, 255, int(110*p)), width=4 if speaking else 2)
        ld.ellipse([x0+26, y+24, x0+138, y+136], fill=(255, 200, 90, int(255*p)) if speaking else (255, 255, 255, int(235*p)))
        ld.text((x0+82, y+80), L, font=F_LET, fill=(8, 10, 16, int(255*p)), anchor="mm")
        ld.text((x0+180, y+80), txt, font=F_OPT, fill=(255, 255, 255, int(255*p)), anchor="lm")
        fr.alpha_composite(lay)
    if t > 37.0:
        a = ease((t-37.0)/0.4)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow_text(lay, (W//2, 1480), "COMMENT YOUR ANSWER ↓", F_SUB, anchor="ma")
        shadow_text(lay, (W//2, 1560), "Solution in 2 days · Follow so you don't miss it", F_SMALL, fill=(200, 205, 215), anchor="ma")
        lay.putalpha(lay.split()[3].point(lambda v: int(v*a))); fr.alpha_composite(lay)
    return fr

def draw(i):
    t = i/FPS
    return (scene_frame(i) if t < END3D else quiz_frame(i)).convert("RGB")

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for tt in sys.argv[2].split(","):
            draw(int(float(tt)*FPS)//2*2).save(f"{BASE}/still_{tt}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                          "-pix_fmt", "yuv420p", sys.argv[1]], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(draw(i).tobytes())
    p.stdin.close(); sys.exit(p.wait())
