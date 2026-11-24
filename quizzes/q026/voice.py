import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Look closely at the nose of this jet engine."),
 "v2": (1.0, "Right in the middle of the giant fan sits a cone, with a white spiral painted on it. You'll find it on thousands of airliners around the world."),
 "v3": (1.0, "When the engine starts, the fan blades blur into an almost invisible disc. But the spiral starts to swirl, and you can see it from far away."),
 "v4": (1.0, "Even at idle, an engine like this can suck in anything that gets within a few meters of its intake. And that's exactly why it's there."),
 "v6": (1.0, "So, why is the spiral painted on the engine?"),
 "oA": (0.95, "A. To warn the ground crew."),
 "oB": (0.95, "B. To scare birds away."),
 "oC": (0.95, "C. To balance the fan."),
 "oD": (0.95, "D. It's the airline's logo."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
