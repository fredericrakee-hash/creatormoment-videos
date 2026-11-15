import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This container ship is longer than three football fields. And it hides a secret, below the waterline."),
 "v2": (1.0, "Let's dive under the water. Look at this strange nose at the front."),
 "v3": (1.0, "Every ship pushes up a big wave, and that wastes fuel. This nose makes its own wave, which cancels out much of the ship's wave."),
 "v4": (1.0, "Smaller waves, less resistance. Big ships can save up to fifteen percent of their fuel."),
 "v6": (1.0, "So, what is this underwater nose called?"),
 "oA": (0.95, "A. Bulbous bow."),
 "oB": (0.95, "B. Keel."),
 "oC": (0.95, "C. Skeg."),
 "oD": (0.95, "D. Ram."),
 "v7": (1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
