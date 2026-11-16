import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This fighter jet is coming in to land on an aircraft carrier, at around two hundred and fifty kilometers per hour."),
 "v2": (1.0, "The runway is tiny, and it's moving. So a hook under the tail grabs one of the steel cables across the deck, and stops the jet in about two seconds."),
 "v3": (1.0, "But watch the engines. The moment the wheels slam onto the deck, the pilot pushes the throttle to full power."),
 "v4": (1.0, "Full power, at the exact moment you want to stop."),
 "v6": (1.0, "So, why does the pilot do this?"),
 "oA": (0.95, "A. To pull the cable tighter."),
 "oB": (0.95, "B. To keep the engines from dying."),
 "oC": (0.95, "C. To steer straight on the deck."),
 "oD": (0.95, "D. In case it has to take off again."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
