import json, re
def make_subs(qdir, starts, lines):
    """starts: {key: t0}; lines: {key: text}. Splits each line into sentences, timed by characters."""
    d = json.load(open(f"{qdir}/audio/durations.json")); out = []
    for k, t0 in starts.items():
        txt = lines[k]; parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', txt) if p.strip()]
        # merge very short parts with the next one
        merged = []
        for p in parts:
            if merged and len(merged[-1]) < 22: merged[-1] += " " + p
            else: merged.append(p)
        tot = sum(len(p) for p in merged); dur = d[k] - 0.25; t = t0
        for p in merged:
            dt = dur*len(p)/tot; out.append((t, t + dt + 0.15, p)); t += dt
    return out
