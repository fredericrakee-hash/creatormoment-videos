import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A jumbo jet, ready for a twelve-hour flight. Full cabin. Full tanks."),
 "v2": (1.0, "Full power… and up it goes."),
 "v3": (1.0, "But just minutes after takeoff, a warning goes off in the cockpit."),
 "v4": (1.0, "The captain decides to turn back to the airport."),
 "v5": (1.0, "And then… this. White trails pour out of both wings."),
 "v6": (1.0, "The plane is spraying tons of fuel into the sky. On purpose. For ten to fifteen minutes."),
 "vq": (1.0, "So, why would pilots throw away tons of fuel?"),
 "oA": (0.95, "A. To cool down the engines."),
 "oB": (0.95, "B. To put out a fire."),
 "oC": (0.95, "C. To mark their position for rescuers."),
 "oD": (0.95, "D. To be light enough to land safely."),
 "v7": (1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
 "a_eng": ("am_onyx", 1.05, "Engine fire. Engine fire."),
}
d = {}
for key, val in lines.items():
    v, sp, t = (V, *val) if len(val) == 2 else val
    s, sr = k.create(t, voice=v, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
