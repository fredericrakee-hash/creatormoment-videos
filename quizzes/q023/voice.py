import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Look at the very end of this airliner's wing."),
 "v2": (1.0, "It doesn't just stop. It bends sharply upwards into a fin that's taller than a person."),
 "v3": (1.0, "And on humid days, you can sometimes see the air spinning off that tip, in long, twisting trails behind the plane."),
 "v4": (1.0, "Airlines even pay to add these fins to older planes that are already flying."),
 "v6": (1.0, "So, why do the wingtips bend upwards?"),
 "oA": (0.95, "A. To make the plane look modern."),
 "oB": (0.95, "B. To stop the wings from shaking."),
 "oC": (0.95, "C. To save fuel."),
 "oD": (0.95, "D. To protect the wing lights."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
