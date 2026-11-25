import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "A jumbo jet on final approach, seconds from touchdown."),
 "v2": (1.0, "Right at the start of the runway, a giant number is painted on the ground: twenty-seven. Each digit is taller than a house."),
 "v3": (1.0, "Now fly to the other end of the very same runway. There, it says zero-nine. Two different numbers, one single strip of asphalt."),
 "v4": (1.0, "And every few years, some airports have to paint brand new numbers, even though the runway hasn't moved an inch."),
 "v6": (1.0, "So, what does the number on the runway mean?"),
 "oA": (0.95, "A. Its length, in hundreds of meters."),
 "oB": (0.95, "B. Its compass direction."),
 "oC": (0.95, "C. The order it was built in."),
 "oD": (0.95, "D. Its distance from the terminal."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
