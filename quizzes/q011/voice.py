import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Seconds before this giant rocket lifts off, something strange happens on the launch pad."),
 "v2": (1.0, "Huge pipes open up, and a flood of water pours across the pad, right under the engines. Almost half a million gallons, in about half a minute."),
 "v3": (1.0, "Then the engines ignite, and all that water bursts into giant white clouds."),
 "v4": (1.0, "And it's not for show. Without it, the launch could damage the rocket itself."),
 "v6": (1.0, "So, why do they flood the launch pad with water?"),
 "oA": (0.95, "A. To cool down the engines."),
 "oB": (0.95, "B. To add extra thrust."),
 "oC": (0.95, "C. To soak up the noise."),
 "oD": (0.95, "D. To wash the pad clean."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
import os
ONLY=os.environ.get('ONLY')
if ONLY: d=json.load(open(f'{QDIR}/audio/durations.json'))
for key,(sp,t) in lines.items():
    if ONLY and key not in ONLY.split(','): continue
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
