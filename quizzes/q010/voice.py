import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Every day, thousands of cars and trucks cross this huge steel bridge."),
 "v2": (1.0, "And every single one of them rolls over this strange metal comb. Two rows of steel teeth, sliding into each other."),
 "v3": (1.0, "Now watch it over many months. Sometimes the teeth push deep together. Sometimes they pull far apart."),
 "v4": (1.0, "The bridge is not broken. Engineers built it like this on purpose."),
 "v6": (1.0, "So, what is this metal comb for?"),
 "oA": (0.95, "A. Room to grow and shrink."),
 "oB": (0.95, "B. Draining rain off the road."),
 "oC": (0.95, "C. Slowing the cars down."),
 "oD": (0.95, "D. Weighing the trucks."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
