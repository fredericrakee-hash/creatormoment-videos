import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "High above a river valley, power cables stretch from one hilltop to the next. And hanging on them: giant orange balls."),
 "v2": (1.0, "Each one is about three feet wide, made of tough plastic or fiberglass, and bolted right around the cable."),
 "v3": (1.0, "You find them where cables span wide valleys, lakes and rivers. Some are orange, some white, some yellow."),
 "v4": (1.0, "They carry no power, and they're definitely not decoration."),
 "v6": (1.0, "So, what are these orange balls for?"),
 "oA": (0.95, "A. To keep the cables from swaying."),
 "oB": (0.95, "B. To show the power is on."),
 "oC": (0.95, "C. To cut down the humming noise."),
 "oD": (0.95, "D. To warn low-flying aircraft."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
