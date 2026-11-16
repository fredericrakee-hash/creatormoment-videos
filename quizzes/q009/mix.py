import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 49.0; N = int(SR*DUR)
rng = np.random.default_rng(9); mix = np.zeros((N, 2)); t = np.arange(N)/SR
A = QDIR + "/audio/"
TD = 21.0
def load(n):
    a, sr = sf.read(A+n+".wav"); a = a.mean(1) if a.ndim > 1 else a
    a = resample_poly(a, SR, sr); return a/np.max(np.abs(a))
def put(sig, at, g=1.0, pan=0.0):
    i = int(at*SR); j = min(N, i+len(sig)); s = sig[:j-i]*g
    mix[i:j, 0] += s*(1-max(0, pan)); mix[i:j, 1] += s*(1+min(0, pan))
def filt(sig, lo=None, hi=None, o=2):
    sos = butter(o, [lo, hi], btype="band", fs=SR, output="sos") if lo and hi else (butter(o, lo, btype="high", fs=SR, output="sos") if lo else butter(o, hi, btype="low", fs=SR, output="sos"))
    return sosfilt(sos, sig)
def win(a, b, fi=0.5, fo=0.5): return np.clip((t-a)/fi, 0, 1)*np.clip((b-t)/fo, 0, 1)
noise = lambda n: rng.standard_normal(n)
scene = win(0, 29.2, 0.4, 0.8)
# wind + sea
for ch in range(2):
    mix[:, ch] += filt(noise(N), 100, 2200)*(0.6+0.4*np.sin(2*np.pi*0.15*t+ch))*0.06*scene
# jet engine: roar (filtered noise) + turbine whine; level follows throttle
thr = np.where(t < TD, 0.35, np.where(t < 24.6, 0.35 + 0.65*np.clip((t-TD)/0.35, 0, 1), np.clip(1.0 - (t-24.6)/1.5*0.92, 0.08, 1.0)))
near = np.clip((t-7.8)/10.0, 0, 1)*(t < 17.9)*0.6 + (t >= 17.9)*1.0 + (t < 7.8)*0.75
roar = filt(noise(N), 60, 1800, 3)
whine = np.sin(2*np.pi*(2600 + 900*thr)*t) + 0.5*np.sin(2*np.pi*(5200 + 1800*thr)*t)
mix += ((roar*0.22*thr**1.2 + whine*0.012*thr)*near*scene)[:, None]
# cut whooshes
for at in (7.8, 17.9):
    n = int(1.0*SR); x = np.arange(n)/SR
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
# touchdown slam + tyre chirp, cable catch twang, deceleration groan
m = int(1.4*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(48 - 15*y)*y)*np.exp(-y*5) + filt(noise(m), 200, 3000)*np.exp(-y*9)*0.6, TD, 0.9)
m = int(0.35*SR); y = np.arange(m)/SR
put(filt(noise(m), 1500, 6000)*np.exp(-y*14), TD+0.02, 0.35)
m = int(2.6*SR); y = np.arange(m)/SR
twang = (np.sin(2*np.pi*(180 - 60*y)*y) + 0.5*np.sin(2*np.pi*(370 - 120*y)*y))*np.exp(-y*1.6)
put(twang + filt(noise(m), 80, 900)*np.exp(-y*1.2)*0.8, TD+0.05, 0.45)
# stat hit
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.6, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(8.0, 28.8, 2.0, 1.0)
mix += (pad*0.02)[:, None]
# quiz bed + ticks
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-29.2)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 29.2 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 28.4, 0.12)
VO = (("v1", 0.3), ("v2", 8.0), ("v3", 18.2), ("v4", 25.6), ("v6", 29.4),
      ("oA", 31.6), ("oB", 33.9), ("oC", 36.7), ("oD", 39.0), ("v7", 42.3))
for n_, at in VO[5:9]:
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at-0.05, 0.12)
voice = np.zeros(N)
for n_, at in VO:
    v = load(n_); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
