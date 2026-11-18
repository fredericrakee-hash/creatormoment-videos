import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This high-speed train gets all of its power from one thin copper wire, hanging above the track."),
 "v2": (1.0, "But look closely at that wire. It doesn't run straight. At one mast, it gets pulled a little to the left. At the next one, a little to the right."),
 "v3": (1.0, "Now ride along on the roof, in slow motion. The wire keeps sliding from one side to the other, mile after mile. Even on a perfectly straight line."),
 "v4": (1.0, "And that zigzag is no mistake. Engineers set it up on purpose."),
 "v6": (1.0, "So, why does the wire zigzag?"),
 "oA": (0.95, "A. To handle strong crosswinds."),
 "oB": (0.95, "B. So the wire can stretch in the heat."),
 "oC": (0.95, "C. To stop it from sparking."),
 "oD": (0.95, "D. So the contact strip wears evenly."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
