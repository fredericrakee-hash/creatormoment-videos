import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 44100; DUR = 43.0; N = int(SR*DUR)
rng = np.random.default_rng(2)
mix = np.zeros((N, 2))
t = np.arange(N)/SR
A = ""+QDIR+"/audio/"

def load(name):
    a, sr = sf.read(A+name+".wav")
    if a.ndim > 1: a = a.mean(1)
    a = resample_poly(a, SR, sr); return a/np.max(np.abs(a))

def put(sig, at, gain=1.0, pan=0.0):
    i = int(at*SR); j = min(N, i+len(sig)); s = sig[:j-i]*gain
    mix[i:j, 0] += s*(1-max(0, pan)); mix[i:j, 1] += s*(1+min(0, pan))

def filt(sig, lo=None, hi=None, order=2):
    if lo and hi: sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    elif lo: sos = butter(order, lo, btype="high", fs=SR, output="sos")
    else: sos = butter(order, hi, btype="low", fs=SR, output="sos")
    return sosfilt(sos, sig)

def env(n, a=0.01, r=0.1):
    e = np.ones(n); ai = min(n//2, int(a*SR)); ri = min(n//2, int(r*SR))
    e[:ai] = np.linspace(0, 1, ai); e[-ri:] *= np.linspace(1, 0, ri); return e

scene = np.clip(t/1.0, 0, 1)*np.clip((27.0-t)/0.8, 0, 1)
# high-altitude wind / air rush (stereo, slowly modulated)
for ch in range(2):
    w = filt(rng.standard_normal(N), 150, 1800)
    mod = 0.7 + 0.3*np.sin(2*np.pi*0.13*t + ch)
    mix[:, ch] += w*mod*scene*0.10
# distant jet engine hum
hum = filt(rng.standard_normal(N), 60, 400)*0.25 + 0.05*np.sin(2*np.pi*72*t)
mix += (hum*scene*0.5)[:, None]
# cinematic drone with rising tension 4-15.6 s
drone = (np.sin(2*np.pi*49*t) + 0.5*np.sin(2*np.pi*73.5*t) + 0.25*np.sin(2*np.pi*98*t))
tens = 0.04 + 0.10*np.clip((t-4)/11.6, 0, 1)*(t < 15.6) + 0.06*(t >= 15.6)
mix += (drone*tens*scene)[:, None]
# riser into the RA
n = int(3.5*SR); tt = np.arange(n)/SR
riser = filt(rng.standard_normal(n), 400, 6000)*(tt/3.5)**2.5
put(riser, 12.1, 0.18)
# impact hit at RA
n = int(1.6*SR); tt = np.arange(n)/SR
hit = (np.sin(2*np.pi*(55 - 20*tt)*tt)*np.exp(-tt*3.0) + filt(rng.standard_normal(n), 30, 300)*np.exp(-tt*6)*0.6)
put(hit, 15.6, 0.55)

# TCAS chime + alerts (cockpit speaker colour)
def chime():
    n = int(0.16*SR); tt = np.arange(n)/SR
    a = np.sin(2*np.pi*1000*tt)*env(n, 0.005, 0.03); b = np.sin(2*np.pi*800*tt)*env(n, 0.005, 0.03)
    return np.concatenate([a, np.zeros(int(0.03*SR)), b])
put(chime(), 4.35, 0.18)
for name, at in (("a_traffic", 4.6), ("a_climb", 15.8), ("a_descend", 17.3)):
    v = filt(load(name), 400, 3000, 4); v = np.tanh(v*2.2)/np.tanh(2.2)
    put(v, at, 0.32)

# radio data blips while the planes "talk"
for k in range(12):
    n = int(0.05*SR); tt = np.arange(n)/SR
    put(np.sin(2*np.pi*(1500 + 250*(k % 3))*tt)*env(n, 0.003, 0.02), 11.6 + k*0.32, 0.05, pan=(-0.6 if k % 2 else 0.6))

# fly-by whoosh (stereo pan L->R)
n = int(3.0*SR); tt = np.arange(n)/SR
wsh = filt(rng.standard_normal(n), 200, 3500)*np.hanning(n)**1.5
for ch, pan in ((0, 1-tt/3.0), (1, tt/3.0)):
    i = int(23.2*SR); mix[i:i+n, ch] += wsh*pan*0.55

# quiz: soft pulse music bed
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-27.2)/0.5)):
    f = notes[(k//2) % 4]; n = int(0.48*SR); tt = np.arange(n)/SR
    tone = (np.sin(2*np.pi*f*tt) + 0.4*np.sin(2*np.pi*2*f*tt) + 0.15*np.sin(2*np.pi*3*f*tt))*np.exp(-tt*4)
    put(tone, 27.2 + k*0.5, 0.06)
# transition swell + option reveal ticks
n = int(0.9*SR); tt = np.arange(n)/SR
put(filt(rng.standard_normal(n), 300, 5000)*(np.sin(np.pi*tt/0.9)**2), 26.4, 0.12)
for at in (30.15, 32.25, 33.75, 35.45):
    n = int(0.12*SR); tt = np.arange(n)/SR
    put(np.sin(2*np.pi*(880 + 700*tt/0.12)*tt)*np.exp(-tt*30), at, 0.12)

# narration (with gentle ducking of the bed)
voice = np.zeros(N)
for name, at in (("v1", 0.3), ("v2", 6.2), ("v3", 11.5), ("v4", 19.3), ("v5", 22.9), ("v6", 27.3),
                 ("oA", 30.2), ("oB", 32.3), ("oC", 33.8), ("oD", 35.5), ("v7", 37.0)):
    v = load(name); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.45*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]
mix += (voice*0.9)[:, None]

mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(""+QDIR+"/audio/mix.wav", mix, SR)
print("ok")
