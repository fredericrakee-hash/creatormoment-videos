import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 48.8; N = int(SR*DUR)
rng = np.random.default_rng(14); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
wA = win(0, 6.8, 0.6, 0.05); wB = win(6.8, 15.2, 0.05, 0.1); wC = win(15.2, 28.4, 0.1, 0.8)
# deep space drone + faint electronic hum
drone = np.sin(2*np.pi*55*t)*0.5 + np.sin(2*np.pi*82.4*t + 0.3)*0.3 + filt(noise(N), 40, 300, 3)*0.6
mix += (drone*(0.05*wA + 0.03*wB + 0.05*wC))[:, None]
mix += ((np.sin(2*np.pi*(1800 + 30*np.sin(2*np.pi*0.2*t))*t)*0.02)*(wA + wC))[:, None]
# shot B: crinkling foil (sparse crackles)
for k in range(140):
    at = rng.uniform(7.0, 15.0); m = int(0.02*SR); y = np.arange(m)/SR
    put(filt(noise(m), 2000, 10000)*np.exp(-y*200), at, rng.uniform(0.03, 0.12), pan=rng.uniform(-0.6, 0.6))
mix += ((filt(noise(N), 1500, 6000))*wB*0.02)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (6.8, 15.2):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 23.8, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(15.2, 28.2, 1.5, 1.0)
mix += (pad*0.02)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-28.4)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 28.4 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 27.6, 0.12)
VO = (("v1", 0.3), ("v2", 7.0), ("v3", 15.4), ("v4", 23.8), ("v6", 28.6),
      ("oA", 31.7), ("oB", 34.1), ("oC", 36.6), ("oD", 39.4), ("v7", 42.3))
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
