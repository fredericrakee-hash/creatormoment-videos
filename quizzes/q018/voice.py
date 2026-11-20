import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A military transport plane, flying low over the desert at dusk. Suddenly, dozens of blinding fireballs burst out of its sides."),
 "v2": (1.0, "Each one is a pellet of burning magnesium, at around two thousand degrees Fahrenheit, and it's gone after just a few seconds."),
 "v3": (1.0, "Fired in quick bursts, they spread out behind the plane like giant glowing wings."),
 "v4": (1.0, "And crews sometimes fire them even when nothing seems to be wrong."),
 "v6": (1.0, "So, why does the plane shoot out these fireballs?"),
 "oA": (0.95, "A. To fool heat-seeking missiles."),
 "oB": (0.95, "B. To signal the troops below."),
 "oC": (0.95, "C. To burn off leftover fuel."),
 "oD": (0.95, "D. To light up the ground for photos."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
