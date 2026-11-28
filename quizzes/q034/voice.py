import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Mars. NASA's Curiosity rover is crawling across the red sand, millions of kilometers away from home."),
 "v2": (1.0, "Each of its six aluminum wheels is about half a meter tall. And every single one of them leaves a strange trail behind."),
 "v3": (1.0, "Look closely at the tracks. Between the zigzag treads, there's a pattern of short and long marks, repeating over and over."),
 "v4": (1.0, "The engineers who built this rover put it there on purpose. And it's not just decoration."),
 "v6": (1.0, "So, what is this pattern in the tracks?"),
 "oA": (0.95, "A. Morse code for J P L."),
 "oB": (0.95, "B. The rover's serial number."),
 "oC": (0.95, "C. Air vents to cool the wheels."),
 "oD": (0.95, "D. Spikes for climbing dunes."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
