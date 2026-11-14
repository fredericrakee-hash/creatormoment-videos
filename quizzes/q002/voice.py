import soundfile as sf, json
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.int8.onnx", "/home/claude/tts/voices-v1.0.bin")
V = "am_michael"
lines = {
 "v1": (1.0, "This rocket booster just fell back from space. It's taller than a ten-story building, and it's coming down tail first."),
 "v2": (1.0, "Then, four strange metal panels unfold at the top. They glow from the heat."),
 "v3": (1.0, "They twist and turn, steering the booster through the air. No pilot on board."),
 "v4": (1.0, "Seconds before impact, the engine fires again."),
 "v5": (1.0, "Legs out. And it lands. On a ship, in the middle of the ocean."),
 "v6": (1.0, "So, what are these steering panels called?"),
 "oA": (0.95, "A. Canards."),
 "oB": (0.95, "B. Air brakes."),
 "oC": (0.95, "C. Grid fins."),
 "oD": (0.95, "D. Ailerons."),
 "v7": (1.05, "Comment your answer below! The solution comes in two days, so follow and don't miss it."),
}
d = {}
for key,(sp,t) in lines.items():
    s, sr = k.create(t, voice=V, speed=sp, lang="en-us")
    sf.write(f"audio/{key}.wav", s, sr); d[key] = round(len(s)/sr, 2)
json.dump(d, open("audio/durations.json","w"), indent=1); print(d)
