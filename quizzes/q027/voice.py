import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A military submarine surfaces at dusk, far out at sea."),
 "v2": (1.0, "Now look closely at its hull. It's covered in thousands of black rubber tiles, glued on one by one, all over the boat."),
 "v3": (1.0, "And look: some of them are missing. You can spot gaps like these on submarines all over the world, and navies say that's perfectly normal."),
 "v4": (1.0, "German U-boats already tested an early version in World War Two. Today, many modern submarines wear this rubber skin."),
 "v6": (1.0, "So, why is the submarine covered in rubber tiles?"),
 "oA": (0.95, "A. To protect it from ice."),
 "oB": (0.95, "B. To keep the crew warm."),
 "oC": (0.95, "C. To hide from sonar."),
 "oD": (0.95, "D. To slide faster through the water."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
