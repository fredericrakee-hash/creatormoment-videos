import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This battle tank is about to fire its main gun. Keep your eyes on the long barrel, right after the shot."),
 "v2": (1.0, "Halfway along it, there's a thick bulge, like a sleeve wrapped around the gun. Many modern tanks have one, like the American M1 Abrams."),
 "v3": (1.0, "Cut it open, and you'd find a ring of small holes, drilled right through the wall of the barrel."),
 "v4": (1.0, "Without this bulge, the crew inside the turret would be in serious trouble after every single shot."),
 "v6": (1.0, "So, what does this bulge on the barrel do?"),
 "oA": (0.95, "A. It cools the hot barrel."),
 "oB": (0.95, "B. It's a silencer for the shot."),
 "oC": (0.95, "C. It's extra armor for the gun."),
 "oD": (0.95, "D. It sucks out the toxic fumes."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
