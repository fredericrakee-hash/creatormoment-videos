import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Train wheels have a big problem. Both wheels sit on one solid steel axle, so they always turn at exactly the same speed."),
 "v2": (1.0, "But in a curve, the outer rail is longer. The outer wheel has to travel further."),
 "v3": (1.0, "So how does a train get around the bend without skidding? Watch the axle closely."),
 "v4": (1.0, "It slides a little bit outward. Now the outer wheel rolls on a bigger circle, and the inner wheel on a smaller one. The train steers itself!"),
 "v6": (1.0, "So, what makes this work?"),
 "oA": (0.95, "A. A hidden differential."),
 "oB": (0.95, "B. Wheels slipping on the rail."),
 "oC": (0.95, "C. Conical wheels."),
 "oD": (0.95, "D. Banked track."),
 "v7": (1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
