import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This tank is racing over rough ground at full speed. The hull is bouncing up and down like a boat in a storm."),
 "v2": (1.0, "But look at the long barrel. It stays locked on the target, no matter how hard the tank pitches."),
 "v3": (1.0, "Sensors feel every single bump, and powerful motors move the barrel the opposite way, many times every second."),
 "v4": (1.0, "That is how a modern tank can hit a target, while it is still driving."),
 "v6": (1.0, "So, what is this system called?"),
 "oA": (0.95, "A. Active suspension."),
 "oB": (0.95, "B. Gun stabilizer."),
 "oC": (0.95, "C. Muzzle brake."),
 "oD": (0.95, "D. Laser rangefinder."),
 "v7": (1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
