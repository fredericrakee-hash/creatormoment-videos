import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Kazakhstan. A space capsule drifts down under a giant parachute, with three people inside, back from the space station."),
 "v2": (1.0, "Even under that giant parachute, it's still falling at seven meters per second. That's about twenty-five kilometers per hour."),
 "v3": (1.0, "Then, less than a second before it hits the ground, a blinding flash and a huge cloud of dust burst out from underneath it."),
 "v4": (1.0, "It happens on every normal return from space. And sometimes, it even sets the dry grass on fire."),
 "v6": (1.0, "So, what is that flash, right before touchdown?"),
 "oA": (0.95, "A. The heat shield blowing off."),
 "oB": (0.95, "B. The parachute being cut loose."),
 "oC": (0.95, "C. Its batteries overheating."),
 "oD": (0.95, "D. Rockets cushioning the landing."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
