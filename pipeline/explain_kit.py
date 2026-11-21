"""Drawing kit for the animated explanation diagrams in solution videos.

A quiz can ship quizzes/qNNN/explain.py with
    SCENES = [scene0, scene1, ...]      # one per sentence in spec["explain"]
    def scene0(k, t, d): ...            # k = Kit, t = seconds since the sentence started, d = its duration
Each scene draws into a 960 x 880 panel (origin top-left) with the Kit methods below.
answer.py shows the panel under a green answer banner while the sentence is spoken.
Style: dark glass panel, thin white lines, gold accent, green = good, red = bad. Keep it clean and grown-up.
"""
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PW, PH, S = 960, 880, 2
FD = "/usr/share/fonts/opentype/inter/"
_fonts = {}
def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FD + ("InterDisplay-Black.otf" if bold else "Inter-SemiBold.otf"), int(size*S))
    return _fonts[key]

WHITE = (255, 255, 255); GOLD = (255, 200, 90); GREEN = (90, 230, 140); RED = (255, 95, 80)
BLUE = (120, 190, 255); GREY = (150, 155, 165); DARK = (20, 24, 32)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def seg(t, a, b):
    """0..1 progress of t between a and b (eased)"""
    return ease((t - a)/max(1e-6, b - a))
def lerp(a, b, k): return a + (b - a)*k
def lerp2(p, q, k): return (lerp(p[0], q[0], k), lerp(p[1], q[1], k))

class Kit:
    def __init__(self, clipframe=None):
        self.img = Image.new("RGBA", (PW*S, PH*S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self._clip = clipframe          # f(frac 0..1) -> RGBA 1080x1920 frame of the clean action clip

    # ---------------------------------------------------------------- helpers
    def _p(self, p): return (p[0]*S, p[1]*S)
    def _c(self, col, a=1.0):
        a = max(0.0, min(1.0, a))
        return (*col[:3], int((col[3] if len(col) > 3 else 255)*a))
    def layer(self):
        """draw something semi-transparent on its own layer: returns (img, draw); call self.merge(img)"""
        im = Image.new("RGBA", self.img.size, (0, 0, 0, 0)); return im, ImageDraw.Draw(im)
    def merge(self, im):
        if im is not self.img: self.img.alpha_composite(im)
    def _tgt(self, a, *cols):
        """draw straight onto the panel when everything is opaque (fast path)"""
        if a >= 0.999 and all(c is None or len(c) == 3 or c[3] == 255 for c in cols): return self.img, self.d
        return self.layer()

    # ---------------------------------------------------------------- primitives (panel coordinates)
    def line(self, p, q, col=WHITE, w=4, prog=1.0, a=1.0):
        if prog <= 0 or a <= 0: return
        im, d = self._tgt(a, col); q2 = lerp2(p, q, min(1, prog))
        d.line([self._p(p), self._p(q2)], fill=self._c(col), width=int(w*S))
        r = w*S/2
        for c in (p, q2): d.ellipse([c[0]*S-r, c[1]*S-r, c[0]*S+r, c[1]*S+r], fill=self._c(col))
        if a < 1 and im is not self.img: im.putalpha(im.split()[3].point(lambda v: int(v*a)))
        self.merge(im)
    def poly(self, pts, col=WHITE, w=4, prog=1.0, a=1.0, closed=False, dash=None):
        """polyline drawn on progressively (prog 0..1 of its length)"""
        if prog <= 0 or a <= 0 or len(pts) < 2: return
        if closed: pts = list(pts) + [pts[0]]
        L = [math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1)]; tot = sum(L); lim = tot*min(1, prog)
        im, d = self._tgt(a, col); acc = 0.0; out = [pts[0]]
        for i, l in enumerate(L):
            if acc + l >= lim:
                out.append(lerp2(pts[i], pts[i+1], (lim - acc)/max(l, 1e-6))); break
            out.append(pts[i+1]); acc += l
        if dash:
            on, off = dash; s_acc = 0.0
            for i in range(len(out)-1):
                p, q = out[i], out[i+1]; l = math.dist(p, q); u = 0.0
                while u < l:
                    ph = (s_acc + u) % (on + off); step = min(l - u, (on - ph) if ph < on else (on + off - ph))
                    if ph < on: d.line([self._p(lerp2(p, q, u/l)), self._p(lerp2(p, q, (u+step)/l))], fill=self._c(col), width=int(w*S))
                    u += max(step, 0.5)
                s_acc += l
        else:
            d.line([self._p(p) for p in out], fill=self._c(col), width=int(w*S), joint="curve")
        if a < 1 and im is not self.img: im.putalpha(im.split()[3].point(lambda v: int(v*a)))
        self.merge(im)
    def arrow(self, p, q, col=GOLD, w=5, prog=1.0, a=1.0, head=22):
        if prog <= 0 or a <= 0: return
        q2 = lerp2(p, q, min(1, prog)); self.line(p, q2, col, w, 1.0, a)
        ang = math.atan2(q2[1]-p[1], q2[0]-p[0])
        h = [q2, (q2[0] - head*math.cos(ang - 0.45), q2[1] - head*math.sin(ang - 0.45)),
             (q2[0] - head*math.cos(ang + 0.45), q2[1] - head*math.sin(ang + 0.45))]
        self.shape(h, fill=col, a=a)
    def shape(self, pts, fill=None, outline=None, w=3, a=1.0):
        if a <= 0: return
        im, d = self._tgt(a, fill, outline)
        d.polygon([self._p(p) for p in pts], fill=self._c(fill, a) if fill else None,
                  outline=self._c(outline, a) if outline else None, width=int(w*S))
        self.merge(im)
    def rect(self, box, fill=None, outline=None, w=3, r=0, a=1.0):
        if a <= 0: return
        im, d = self._tgt(a, fill, outline); b = [box[0]*S, box[1]*S, box[2]*S, box[3]*S]
        d.rounded_rectangle(b, radius=r*S, fill=self._c(fill, a) if fill else None, outline=self._c(outline, a) if outline else None, width=int(w*S))
        self.merge(im)
    def circle(self, c, r, fill=None, outline=None, w=3, a=1.0):
        if a <= 0 or r <= 0: return
        im, d = self._tgt(a, fill, outline)
        d.ellipse([(c[0]-r)*S, (c[1]-r)*S, (c[0]+r)*S, (c[1]+r)*S], fill=self._c(fill, a) if fill else None,
                  outline=self._c(outline, a) if outline else None, width=int(w*S))
        self.merge(im)
    def arc(self, c, r, a0, a1, col=WHITE, w=4, a=1.0):
        """angles in degrees, 0 = right, clockwise (PIL convention)"""
        if a <= 0 or r <= 0: return
        im, d = self._tgt(a, col)
        d.arc([(c[0]-r)*S, (c[1]-r)*S, (c[0]+r)*S, (c[1]+r)*S], a0, a1, fill=self._c(col, a), width=int(w*S))
        self.merge(im)
    def text(self, xy, txt, size=40, col=WHITE, a=1.0, anchor="la", bold=True, shadow=True):
        if a <= 0: return
        im, d = self.layer(); f = font(size, bold); p = self._p(xy)
        if shadow:
            d.text((p[0]+3, p[1]+4), txt, font=f, fill=(0, 0, 0, int(160*a)), anchor=anchor)
            im = im.filter(ImageFilter.GaussianBlur(5)); d = ImageDraw.Draw(im)
        d.text(p, txt, font=f, fill=self._c(col, a), anchor=anchor)
        self.merge(im)
    def tag(self, xy, txt, col=GOLD, a=1.0, size=26):
        """small pill label"""
        if a <= 0: return
        f = font(size, False); tw = self.d.textlength(txt, font=f)/S
        self.rect((xy[0], xy[1], xy[0] + tw + 32, xy[1] + size + 22), fill=(0, 0, 0, 150), outline=col, w=2, r=(size + 22)/2, a=a)
        self.text((xy[0] + 16, xy[1] + 11), txt, size, col, a, bold=False, shadow=False)
    def cross(self, c, r=40, col=RED, w=8, a=1.0):
        self.line((c[0]-r, c[1]-r), (c[0]+r, c[1]+r), col, w, a=a); self.line((c[0]-r, c[1]+r), (c[0]+r, c[1]-r), col, w, a=a)
    def check(self, c, r=40, col=GREEN, w=8, a=1.0, prog=1.0):
        self.poly([(c[0]-r, c[1]), (c[0]-r*0.3, c[1]+r*0.65), (c[0]+r, c[1]-r*0.7)], col, w, prog=prog, a=a)
    def waves(self, x0, x1, y, amp=6, n=8, col=BLUE, w=3, t=0.0, a=1.0):
        pts = [(x, y + amp*math.sin((x - x0)/(x1 - x0)*n*2*math.pi + t*3)) for x in range(int(x0), int(x1)+1, 6)]
        self.poly(pts, col, w, a=a)
    def clip(self, frac, box=(0, 0, PW, PH), a=1.0, dim=0.0):
        """put a frame of the clean action clip into box (cover-cropped)"""
        if self._clip is None or a <= 0: return
        fr = self._clip(frac).convert("RGBA"); bw, bh = int((box[2]-box[0])*S), int((box[3]-box[1])*S)
        sc = max(bw/fr.width, bh/fr.height); fr = fr.resize((int(fr.width*sc)+1, int(fr.height*sc)+1), Image.LANCZOS)
        ox, oy = (fr.width - bw)//2, (fr.height - bh)//2; fr = fr.crop((ox, oy, ox + bw, oy + bh))
        if dim: fr = Image.blend(fr, Image.new("RGBA", fr.size, (6, 8, 14, 255)), dim)
        m = Image.new("L", fr.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, bw-1, bh-1], radius=26*S, fill=int(255*a))
        self.img.paste(fr, (int(box[0]*S), int(box[1]*S)), m)

    def render(self):
        """-> RGBA PW x PH"""
        return self.img.resize((PW, PH), Image.LANCZOS)
