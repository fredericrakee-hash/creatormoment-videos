import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Almost every cargo ship in the world has this painted on its side: a circle, crossed by a line, with two letters next to it."),
 "v2": (1.0, "And right beside it, a ladder of short lines, each one marked with letters."),
 "v3": (1.0, "In the harbor, the cranes put container after container on board, and the whole ship slowly sinks deeper and deeper."),
 "v4": (1.0, "Captains check this mark before every departure. And in a river, the very same ship floats even deeper than at sea."),
 "v6": (1.0, "So, what is this symbol on the hull for?"),
 "oA": (0.95, "A. It's the shipyard's logo."),
 "oB": (0.95, "B. It shows where tugboats push."),
 "oC": (0.95, "C. It marks the engine room."),
 "oD": (0.95, "D. How low it may sit in the water."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
