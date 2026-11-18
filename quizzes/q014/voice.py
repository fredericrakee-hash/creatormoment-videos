import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This satellite is worth a fortune. And yet, it's wrapped in what looks like crumpled gold foil."),
 "v2": (1.0, "But look closer. It's not real gold. It's paper-thin plastic film, coated with metal, and stacked many sheets deep."),
 "v3": (1.0, "You'll find it on satellites, on space probes, even on the old Moon landers. All of them wrapped up like a chocolate bar."),
 "v4": (1.0, "And no, it's not there for the looks. Engineers say it's essential."),
 "v6": (1.0, "So, why are satellites wrapped in this foil?"),
 "oA": (0.95, "A. To control its temperature."),
 "oB": (0.95, "B. To block radio interference."),
 "oC": (0.95, "C. To be easier to spot from Earth."),
 "oD": (0.95, "D. To boost its solar power."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
