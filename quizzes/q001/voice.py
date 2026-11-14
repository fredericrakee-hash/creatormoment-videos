import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json, os
os.makedirs(QDIR+"/audio", exist_ok=True)
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (V, 1.0, "Two planes. Same altitude. Heading straight for each other."),
 "v2": (V, 1.0, "But nobody panics. Because a hidden system in both cockpits just kicked in."),
 "v3": (V, 1.0, "The two planes actually talk to each other, and agree on a plan."),
 "v4": (V, 1.0, "One crew is told to climb. The other, to descend."),
 "v5": (V, 1.0, "And just like that, they pass safely. Hundreds of feet apart."),
 "v6": (V, 1.0, "So, what is this lifesaving system called?"),
 "oA": (V, 0.95, "A. G, P, W, S."),
 "oB": (V, 0.95, "B. T, CAS."),
 "oC": (V, 0.95, "C. I, L, S."),
 "oD": (V, 0.95, "D. ATIS."),
 "v7": (V, 1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
 "a_traffic": ("am_onyx", 1.05, "Traffic. Traffic."),
 "a_climb": ("am_onyx", 1.05, "Climb. Climb."),
 "a_descend": ("am_onyx", 1.05, "Descend. Descend."),
}
d = {}
for key,(v,sp,t) in lines.items():
    s, sr = k.create(t, voice=v, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(QDIR+"/audio/durations.json","w"), indent=1); print(d)
