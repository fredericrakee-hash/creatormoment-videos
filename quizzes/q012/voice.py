import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Look closely at the back edge of this airliner's wing."),
 "v2": (1.0, "A row of thin black rods sticks out, all pointing backwards. You will find them on the tail and the rudder too."),
 "v3": (1.0, "Pilots check them on the walk-around before a flight. And they matter most when the plane flies through rain, snow, or dust."),
 "v4": (1.0, "They are tiny, but almost every airliner in the sky carries them."),
 "v6": (1.0, "So, what are these little rods for?"),
 "oA": (0.95, "A. Measuring the airspeed."),
 "oB": (0.95, "B. Draining static electricity."),
 "oC": (0.95, "C. Cutting down wing noise."),
 "oD": (0.95, "D. Keeping birds away."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
