import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A fully loaded semi truck, coming down a steep mountain pass. Smoke is pouring from its wheels, and it's getting faster and faster."),
 "v2": (1.0, "Then the driver swerves off the highway, straight into a lane full of deep, loose gravel."),
 "v3": (1.0, "The wheels dig in, gravel flies everywhere, and the giant truck grinds to a halt."),
 "v4": (1.0, "Now it's stuck, and it'll take a tow truck to pull it free. But the driver did all of this on purpose."),
 "v6": (1.0, "So, why did he steer into the gravel?"),
 "oA": (0.95, "A. To cool down the hot tires."),
 "oB": (0.95, "B. To let the traffic behind him pass."),
 "oC": (0.95, "C. His brakes gave out."),
 "oD": (0.95, "D. To get around a crash ahead."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
