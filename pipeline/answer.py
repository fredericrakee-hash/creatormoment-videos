"""Build the solution video for a quiz.

Usage:  python3 pipeline/answer.py quizzes/q001/spec.json OUT.mp4

spec.json fields used:
  num, question (list of 2 title lines), options [4 strings], correct (0-3),
  answer_full ("TCAS, the Traffic Collision Avoidance System"),
  explain  [2-4 short spoken sentences explaining it],
  recap    (one spoken sentence reminding what the quiz video showed),
  video    (path or URL of the published quiz video, relative to repo root),
  clip_video (path of the CLEAN action clip without text overlays, e.g. videos/q001-clean.mp4)
  clip     [start, end] seconds of clip_video to reuse (~10-14 s),
  followup (optional: {"question": "...", "options": [...]}  -> teaser for the next quiz)
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.signal import resample_poly
from kokoro_onnx import Kokoro

W, H, FPS, SR = 1080, 1920, 30, 44100
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = "/usr/share/fonts/opentype/inter/"
def F(n, s): return ImageFont.truetype(FD+n, s)
F_TITLE, F_SUB, F_TAG = F("InterDisplay-Black.otf", 84), F("Inter-SemiBold.otf", 50), F("Inter-SemiBold.otf", 30)
F_Q, F_OPT, F_LET, F_SMALL = F("InterDisplay-Black.otf", 70), F("InterDisplay-Black.otf", 62), F("InterDisplay-Black.otf", 58), F("Inter-SemiBold.otf", 38)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)

def shadow_text(base, xy, txt, font, fill=(255, 255, 255), anchor="la", alpha=1.0):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((xy[0]+2, xy[1]+3), txt, font=font, fill=(0, 0, 0, 170), anchor=anchor)
    lay = lay.filter(ImageFilter.GaussianBlur(6))
    ImageDraw.Draw(lay).text(xy, txt, font=font, fill=fill, anchor=anchor)
    if alpha < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v*alpha)))
    base.alpha_composite(lay)

def wrap(d, txt, font, maxw):
    out, cur = [], ""
    for w in txt.split():
        t = (cur+" "+w).strip()
        if d.textlength(t, font=font) > maxw and cur: out.append(cur); cur = w
        else: cur = t
    return out + [cur]

def main(spec_path, out):
    spec = json.load(open(spec_path)); n = spec["num"]
    tmp = tempfile.mkdtemp()
    k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
    def say(txt, speed=1.0):
        s, sr = k.create(txt, voice="am_michael", speed=speed, lang="en-us")
        s = resample_poly(s, SR, sr); return s/np.max(np.abs(s))
    L = "ABCD"[spec["correct"]]
    lines = [("recap", f"Quiz number {n}. {spec['recap']}"), ("drum", "So, what's the answer?")]
    lines += [("reveal", f"It's {L}! {spec['answer_full']}.")]
    lines += [(f"e{i}", s) for i, s in enumerate(spec["explain"])]
    if spec.get("followup"):
        lines.append(("fu", "Bonus question: " + spec["followup"]["question"] + " Tell me in the comments!"))
    lines.append(("out", "Did you get it right? Follow for a new quiz every day!"))
    audio = {key: say(t) for key, t in lines}

    # timeline
    t = 0.4; tl = {}
    for key, _ in lines:
        if key == "reveal": t += 1.2
        tl[key] = t; t += len(audio[key])/SR + 0.35
    dur = t + 1.0
    clip0, clip1 = spec["clip"]; clip_len = clip1 - clip0
    card_start = tl["drum"] - 0.3

    # source clip frames
    cv = spec.get("clip_video", spec["video"])
    src = cv if cv.startswith("http") else os.path.join(REPO, cv)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(clip0), "-t", str(clip_len), "-i", src,
                    "-vf", f"fps={FPS},scale={W}:{H}", f"{tmp}/c%04d.jpg"], check=True)
    nclip = len([f for f in os.listdir(tmp) if f.startswith("c")])
    def clipframe(i):
        i = max(1, min(nclip, i+1)); return Image.open(f"{tmp}/c{i:04d}.jpg").convert("RGBA")
    last = clipframe(nclip-1).convert("RGB").filter(ImageFilter.GaussianBlur(26))
    bg = Image.blend(last, Image.new("RGB", (W, H), (6, 8, 14)), 0.62).convert("RGBA")

    exp_txt = {tl[f"e{i}"]: s for i, s in enumerate(spec["explain"])}
    def frame(i):
        tt = i/FPS
        if tt < card_start:
            # replay of the quiz action, slow push, darkened top/bottom
            fr = clipframe(int(tt/card_start*(nclip-1)))
            shadow_text(fr, (60, 520), "THE ANSWER", F_TITLE, alpha=ease((tt-0.2)/0.4))
            shadow_text(fr, (60, 615), f"QUIZ #{n}", F_TITLE, fill=(255, 200, 90), alpha=ease((tt-0.4)/0.4))
            d = ImageDraw.Draw(fr)
            for j, ln in enumerate(wrap(d, spec["recap"], F_SUB, W-140)):
                shadow_text(fr, (W//2, 1560 + j*64), ln, F_SUB, anchor="ma")
            fr = Image.blend(fr, bg, ease((tt-(card_start-0.6))/0.6))
        else:
            fr = bg.copy()
            shadow_text(fr, (W//2, 300), spec["question"][0], F_Q, anchor="ma")
            shadow_text(fr, (W//2, 385), spec["question"][1], F_Q, fill=(255, 200, 90), anchor="ma")
            rv = ease((tt-tl["reveal"])/0.35)
            for j, opt in enumerate(spec["options"]):
                y = 560 + j*190; x0, x1 = 90, W-90
                ok = j == spec["correct"]
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
                fade = 1 - 0.65*rv if not ok else 1
                if ok and rv > 0:
                    ld.rounded_rectangle([x0, y, x1, y+150], radius=28, fill=(40, 190, 100, int(230*rv)), outline=(120, 255, 170, 255), width=4)
                else:
                    ld.rounded_rectangle([x0, y, x1, y+150], radius=28, fill=(255, 255, 255, int(30*fade)), outline=(255, 255, 255, int(110*fade)), width=2)
                ld.ellipse([x0+24, y+21, x0+132, y+129], fill=(255, 255, 255, int(235*fade)))
                ld.text((x0+78, y+75), "ABCD"[j], font=F_LET, fill=(8, 10, 16, int(255*fade)), anchor="mm")
                ld.text((x0+170, y+75), opt + ("  ✓" if ok and rv > 0.5 else ""), font=F_OPT, fill=(255, 255, 255, int(255*fade)), anchor="lm")
                fr.alpha_composite(lay)
            cur = None
            for ts, s in exp_txt.items():
                if tt >= ts: cur = s
            if "fu" in tl and tt >= tl["fu"]: cur = "BONUS: " + spec["followup"]["question"]
            if "out" in tl and tt >= tl["out"]: cur = "Did you get it right? Follow for daily quizzes!"
            if cur:
                d = ImageDraw.Draw(fr)
                for j, ln in enumerate(wrap(d, cur, F_SUB, W-140)):
                    shadow_text(fr, (W//2, 1360 + j*64), ln, F_SUB, anchor="ma")
        d = ImageDraw.Draw(fr)
        d.rounded_rectangle([56, 112, 290, 166], radius=12, fill=(0, 0, 0, 120), outline=(255, 255, 255, 90), width=2)
        d.text((173, 139), f"ANSWER #{n}", font=F_TAG, fill=(255, 255, 255), anchor="mm")
        return fr.convert("RGB")

    vtmp = f"{tmp}/v.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                          "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    for i in range(int(dur*FPS)): p.stdin.write(frame(i).tobytes())
    p.stdin.close(); p.wait()

    # audio: soft bed + drum roll + reveal hit + voice
    N = int(dur*SR); mix = np.zeros(N); tt = np.arange(N)/SR; rng = np.random.default_rng(1)
    for kk in range(int(dur/0.5)):
        f = [110, 130.81, 164.81, 146.83][(kk//2) % 4]; m = int(0.48*SR); x = np.arange(m)/SR
        tone = (np.sin(2*np.pi*f*x) + 0.4*np.sin(2*np.pi*2*f*x))*np.exp(-x*4)
        i0 = int(kk*0.5*SR); j0 = min(N, i0+m); mix[i0:j0] += tone[:j0-i0]*0.05
    r0 = int((tl["reveal"]-1.4)*SR); m = int(1.3*SR); x = np.arange(m)/SR
    roll = rng.standard_normal(m)*(0.5+0.5*np.sin(2*np.pi*22*x)**2)*(x/1.3)*0.12
    mix[r0:r0+m] += roll
    h0 = int(tl["reveal"]*SR); m = int(1.0*SR); x = np.arange(m)/SR
    mix[h0:h0+m] += (np.sin(2*np.pi*(660+220*(x > 0.08))*x)*np.exp(-x*5))*0.25
    for key, _ in lines:
        a = audio[key]; i0 = int(tl[key]*SR); j0 = min(N, i0+len(a)); mix[i0:j0] += a[:j0-i0]*0.9
    mix /= max(1.0, np.abs(mix).max()/0.95)
    sf.write(f"{tmp}/a.wav", np.stack([mix, mix], 1), SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", f"{tmp}/a.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("ok", out, round(dur, 1), "s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
