import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 48.5; N = int(SR*DUR)
rng = np.random.default_rng(17); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 27.6
w3d = win(0, E3, 0.8, 0.8)
# high valley: steady wind (stronger in the drone shots), river below, birds, faint line hum
wind = filt(noise(N), 80, 900, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.11*t) + 0.2*np.sin(2*np.pi*0.37*t))
mix += (wind*0.06*w3d*(1 + 0.6*win(23.4, E3, 0.1, 0.5)))[:, None]
mix += (filt(noise(N), 1500, 6000)*0.010*w3d)[:, None]
hum = (np.sin(2*np.pi*100*t) + 0.5*np.sin(2*np.pi*200*t) + 0.25*np.sin(2*np.pi*300*t))*(0.8 + 0.2*np.sin(2*np.pi*0.3*t))
mix += (hum*0.006*w3d)[:, None]
for k in range(8):
    at = rng.uniform(1, 22); m = int(0.35*SR); y = np.arange(m)/SR
    f0 = rng.uniform(2200, 3400)
    put(np.sin(2*np.pi*(f0 - 900*y/0.35)*y)*np.exp(-y*8), at, 0.010, rng.uniform(-0.7, 0.7))
n = int(1.0*SR); x = np.arange(n)/SR
for at in (8.4, 16.0, 23.4):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.25)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 23.6, 0.45)
for k, at in enumerate((9.2, 11.2, 13.6, 17.3, 18.0, 18.6, 20.4, 21.1, 21.8)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(8.4, 27.4, 1.5, 1.0)
mix += (pad*0.018)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 8.6), ("v3", 16.2), ("v4", 23.6), ("v6", 27.9),
      ("oA", 30.4), ("oB", 33.4), ("oC", 36.4), ("oD", 38.9), ("v7", 41.8))
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
