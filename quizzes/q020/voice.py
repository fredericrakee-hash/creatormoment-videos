import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Most railway lines in the world are built on this: a thick bed of sharp, crushed rock, piled up under the rails and around the concrete beams."),
 "v2": (1.0, "Not smooth pebbles. Not sand. Always rough, angular stones with sharp edges."),
 "v3": (1.0, "Then a freight train thunders past. Thousands of tons, pushing down and sideways on every single stone."),
 "v4": (1.0, "And yet, once the train is gone, the rails are exactly where they were before."),
 "v6": (1.0, "So, why are railway lines built on crushed stone?"),
 "oA": (0.95, "A. To stop sparks from starting fires."),
 "oB": (0.95, "B. To lock the track in place."),
 "oC": (0.95, "C. To keep animals off the line."),
 "oD": (0.95, "D. It's leftover rock from tunnels."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
