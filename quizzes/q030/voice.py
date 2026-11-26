import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Chicago, in the middle of winter. It is minus twenty degrees, and the railway is buried in snow."),
 "v2": (1.0, "Then, right where one track splits into two, long rows of flames light up along the rails. And nobody tries to put them out."),
 "v3": (1.0, "A commuter train rolls straight through the fire, without even slowing down."),
 "v4": (1.0, "The railway lights these flames on purpose, every winter. Its busiest junction here carries more than three hundred trains a day."),
 "v6": (1.0, "So, why are there flames burning on the tracks?"),
 "oA": (0.95, "A. To keep the switches from freezing."),
 "oB": (0.95, "B. To warn cars at the crossing."),
 "oC": (0.95, "C. To burn off spilled diesel."),
 "oD": (0.95, "D. To keep track workers warm."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
