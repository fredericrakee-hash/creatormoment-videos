import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This ship can push through sea ice more than two meters thick. And it has no blade, no saw, and no drill."),
 "v2": (1.0, "Look at the front of the hull. It isn't sharp like a normal ship. It's rounded, and it slopes gently backwards."),
 "v3": (1.0, "It moves slowly. In the thickest ice, it backs off and charges again, over and over."),
 "v4": (1.0, "And behind it, the frozen sea is left in pieces. An open channel, for other ships to follow."),
 "v6": (1.0, "So, how does an icebreaker actually break the ice?"),
 "oA": (0.95, "A. A sharp steel edge cuts through it."),
 "oB": (0.95, "B. Its hull heats the ice and melts it."),
 "oC": (0.95, "C. It crushes it with its own weight."),
 "oD": (0.95, "D. Strong vibrations shatter it."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
