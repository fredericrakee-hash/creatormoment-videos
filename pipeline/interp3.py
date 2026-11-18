# usage: python3 interp.py QDIR "A:0:234,B:234:537,C:537:876"
import sys, os, subprocess, glob, shutil
Q = sys.argv[1]
for spec in sys.argv[2].split(","):
    s, a, b = spec.split(":"); a, b = int(a), int(b)
    ev = [i for i in range(a, b) if i % 3 == 0 and os.path.exists(f"{Q}/frames/f{i:04d}.png")]
    first = ev[0]
    lst = f"{Q}/list_{s}.txt"
    with open(lst, "w") as f:
        for i in ev: f.write(f"file '{Q}/frames/f{i:04d}.png'\nduration {1/10}\n")
    out = f"{Q}/interp/{s}"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    tmp = f"{Q}/interp/tmp_{s}"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-vf", "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                    "-q:v", "2", f"{tmp}/%05d.jpg"], check=True)
    # extracted n (1-based) == frame first + n - 1  -> comp expects index i - a + 1
    for p in sorted(glob.glob(f"{tmp}/*.jpg")):
        n = int(os.path.basename(p)[:5]); i = first + n - 1
        if i >= b: continue
        os.rename(p, f"{out}/{i - a + 1:05d}.jpg")
    shutil.rmtree(tmp)
    print(s, len(os.listdir(out)))
