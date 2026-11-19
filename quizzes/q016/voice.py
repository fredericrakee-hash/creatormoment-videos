import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Look at the edge of almost any car windshield. There's a black band, and then a pattern of tiny black dots."),
 "v2": (1.0, "The dots start big, then get smaller and smaller, until they fade into the clear glass."),
 "v3": (1.0, "It's not a sticker, and it's not paint you can scrape off. It's ceramic, baked right into the glass at the factory."),
 "v4": (1.0, "And without it, your windshield could one day come loose."),
 "v6": (1.0, "So, what is this black frame really for?"),
 "oA": (0.95, "A. To hide the radio antenna."),
 "oB": (0.95, "B. To protect the glue from UV light."),
 "oC": (0.95, "C. To stop the glass from fogging up."),
 "oD": (0.95, "D. To make the glass stronger."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
