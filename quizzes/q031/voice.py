import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "Taipei, Taiwan. A typhoon hits the city, and Taipei 101, over five hundred meters tall, takes the full force of the wind."),
 "v2": (1.0, "But high up inside, between floors eighty-seven and ninety-two, hangs a giant golden ball made of steel plates. It weighs six hundred and sixty tons."),
 "v3": (1.0, "When the gusts push the building, the ball starts to move. In a typhoon in 2015, it swung a whole meter."),
 "v4": (1.0, "And it's not hidden away. Visitors can walk right up to it."),
 "v6": (1.0, "So, why does this skyscraper have a giant ball hanging inside?"),
 "oA": (0.95, "A. It's a giant art sculpture."),
 "oB": (0.95, "B. It's an emergency water tank."),
 "oC": (0.95, "C. To cancel out the swaying."),
 "oD": (0.95, "D. It stores power for the elevators."),
 "v7": (1.05, "Comment your answer below! The solution comes tomorrow, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"{QDIR}/audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open(f"{QDIR}/audio/durations.json","w"), indent=1); print(d)
