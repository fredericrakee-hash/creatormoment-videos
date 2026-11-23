import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Look at the roof of almost any new car."),
 "v2": (1.0, "Right at the back sits this little fin, shaped like a shark's. Hard plastic, painted in the car's colour, and only a few inches tall."),
 "v3": (1.0, "Older cars didn't have it at all. Today, you'll find it on a huge number of new models, from small city cars to big SUVs."),
 "v4": (1.0, "It looks like a design detail. But without it, your car would lose more than you think."),
 "v6": (1.0, "So, what is this fin really for?"),
 "oA": (0.95, "A. Better aerodynamics."),
 "oB": (0.95, "B. It hides the antennas."),
 "oC": (0.95, "C. It protects against lightning."),
 "oD": (0.95, "D. It cools the electronics."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
