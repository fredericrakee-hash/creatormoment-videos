import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This cargo ship is more than two hundred and fifty meters long, and right now it's standing on dry land, in a dry dock."),
 "v2": (1.0, "Now look at the bottom. Almost the entire part that's normally underwater is painted the same deep red."),
 "v3": (1.0, "Before the dock is flooded again, workers spray on fresh paint, coat after coat, over the whole underwater hull."),
 "v4": (1.0, "You'll see this red on cargo ships, tankers and warships all over the world. And it's not just for looks."),
 "v6": (1.0, "So, why is the bottom of a ship painted red?"),
 "oA": (0.95, "A. Red paint is the cheapest."),
 "oB": (0.95, "B. To keep barnacles off it."),
 "oC": (0.95, "C. So divers can find the hull."),
 "oD": (0.95, "D. To hide rust stains."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
