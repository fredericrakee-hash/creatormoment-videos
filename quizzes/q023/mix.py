import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 45.0; N = int(SR*DUR)
rng = np.random.default_rng(12); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
wA = win(0, 4.2, 0.4, 0.05); wB = win(4.2, 12.6, 0.05, 0.1); wC = win(12.6, 21.0, 0.1, 0.1); wD = win(21.0, 26.6, 0.1, 0.8)
# airflow roar + engine drone
for ch in range(2):
    mix[:, ch] += filt(noise(N), 150, 3500)*(0.7+0.3*np.sin(2*np.pi*0.17*t+ch))*(0.10*wA + 0.16*wB + 0.14*wC + 0.10*wD)
drone = filt(noise(N), 40, 260, 3) + 0.3*np.sin(2*np.pi*92*t)
mix += (drone*(0.18*wA + 0.10*wB + 0.08*wC + 0.2*wD))[:, None]
# rain in the cloud: dense ticking + hiss
# vortex: slow swirling whoosh in shot C
sw = filt(noise(N), 200, 1800)*(0.6+0.4*np.sin(2*np.pi*0.9*t))
mix += (sw*0.10*wC)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (4.2, 12.6, 21.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 21.4, 0.35)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(4.2, 26.2, 2.0, 1.0)
mix += (pad*0.022)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-26.6)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 26.6 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 25.8, 0.12)
VO = (("v1", 0.3), ("v2", 4.4), ("v3", 12.8), ("v4", 21.2), ("v6", 26.8),
      ("oA", 29.4), ("oB", 31.8), ("oC", 34.5), ("oD", 36.4), ("v7", 38.8))
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
