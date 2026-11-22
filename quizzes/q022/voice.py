import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Florida, early evening. A rocket stands on the launch pad, a few minutes before liftoff."),
 "v2": (1.0, "But look closely at its side: part of the white body is covered in a rough, crusty layer, and wisps of white vapor drift away from it."),
 "v3": (1.0, "Then the engines light up. And as the rocket climbs off the pad, big white sheets and chunks break loose and tumble down past the flames."),
 "v4": (1.0, "Nothing went wrong. It happens on many launches, and it's completely normal."),
 "v6": (1.0, "So, what is falling off the rocket?"),
 "oA": (0.95, "A. Ice from the super-cold fuel."),
 "oB": (0.95, "B. Paint peeling off in the heat."),
 "oC": (0.95, "C. Foam from the launch pad water."),
 "oD": (0.95, "D. Pieces of the heat shield."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
