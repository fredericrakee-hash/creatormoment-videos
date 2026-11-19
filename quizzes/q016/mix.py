import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 45.0; N = int(SR*DUR)
rng = np.random.default_rng(16); mix = np.zeros((N, 2)); t = np.arange(N)/SR
A = QDIR + "/audio/"
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
w3d = win(0, 25.2, 0.8, 0.8)
# evening car park: distant traffic, birds, a soft breeze; muffled inside the car (shot C)
traffic = filt(noise(N), 60, 700, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.07*t))
outside = w3d*(1 - 0.8*win(13.2, 21.0, 0.1, 0.1))
mix += (traffic*0.05*outside)[:, None]
mix += (filt(noise(N), 800, 4000)*0.012*outside)[:, None]
mix += (filt(noise(N), 40, 200, 3)*0.05*win(13.2, 21.0, 0.1, 0.1))[:, None]
for k in range(10):
    at = rng.uniform(1, 12); m = int(0.25*SR); y = np.arange(m)/SR
    f0 = rng.uniform(3000, 4500)
    put(np.sin(2*np.pi*(f0 + 800*np.sin(2*np.pi*14*y))*y)*np.exp(-y*12), at, 0.012, rng.uniform(-0.7, 0.7))
n = int(1.0*SR); x = np.arange(n)/SR
for at in (7.5, 13.2, 21.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.25)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 21.2, 0.45)
# glassy shimmer on the dots
for k in range(4):
    m = int(1.5*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1320*(1 + k*0.25))*y)*np.exp(-y*2.5), 8.3 + k*1.1, 0.025, pan=0.3 - 0.2*k)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(7.5, 25.0, 1.5, 1.0)
mix += (pad*0.018)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-25.2)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 25.2 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 24.4, 0.12)
VO = (("v1", 0.3), ("v2", 7.7), ("v3", 13.4), ("v4", 21.2), ("v6", 25.4),
      ("oA", 27.9), ("oB", 30.3), ("oC", 33.2), ("oD", 36.0), ("v7", 38.5))
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
