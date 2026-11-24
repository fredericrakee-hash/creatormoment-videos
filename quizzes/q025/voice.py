import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A wet autumn morning. A heavy freight train has to pull away, uphill."),
 "v2": (1.0, "The driver opens the throttle, and the wheels just spin on the wet, slippery rails. The train barely moves."),
 "v3": (1.0, "Then, right in front of the wheels, small pipes blast a fine, brownish jet straight onto the rails."),
 "v4": (1.0, "Seconds later, the wheels bite, and thousands of tons start to roll. A modern locomotive carries hundreds of kilos of this stuff on board."),
 "v6": (1.0, "So, what is the locomotive blasting onto the rails?"),
 "oA": (0.95, "A. Steam to dry the rails."),
 "oB": (0.95, "B. Salt to melt the ice."),
 "oC": (0.95, "C. Oil to protect the wheels."),
 "oD": (0.95, "D. Sand, for more grip."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
