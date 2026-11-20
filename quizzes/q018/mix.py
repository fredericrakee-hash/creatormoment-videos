import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.0; N = int(SR*DUR)
rng = np.random.default_rng(18); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 29.4
w3d = win(0, E3, 0.8, 0.8)
# turboprop drone: 4 engines, prop blade-pass buzz + broadband rush; muffled in the ground shot
rush = filt(noise(N), 60, 1200, 2)*(0.8 + 0.2*np.sin(2*np.pi*0.2*t))
air = w3d*(1 - 0.6*win(18.6, 24.6, 0.1, 0.1))
mix += (rush*0.07*air)[:, None]
bp = sum(np.sin(2*np.pi*(68.0 + 0.4*k)*t + k) for k in range(4)) + 0.5*sum(np.sin(2*np.pi*(136.0 + 0.8*k)*t) for k in range(4))
mix += (filt(bp, 40, 600)*0.02*air)[:, None]
# ground shot: distant rumble rolling in
mix += (filt(noise(N), 30, 300, 3)*0.08*win(18.6, 24.6, 0.3, 0.1))[:, None]
# flare ejections: sharp pops + fizz/hiss for each salvo
def pop(at, g):
    m = int(0.5*SR); y = np.arange(m)/SR
    put(filt(noise(m), 600, 7000)*np.exp(-y*30)*1.0 + filt(noise(m), 2000, 9000)*np.exp(-y*5)*0.25, at, g, rng.uniform(-0.5, 0.5))
for k in range(14): pop(5.0 + 0.24*k, 0.16)
for k in range(22): pop(11.2 + 0.24*k, 0.12)
for k in range(12): pop(19.0 + 0.24*k, 0.05)
for at in (25.3, 25.95, 26.6, 27.25): pop(at, 0.22)
hiss = filt(noise(N), 2500, 9000)*(win(5.0, 9.5, 0.2, 1.5) + 0.8*win(11.2, 17.0, 0.2, 1.5) + 0.3*win(19.0, 23.0, 0.2, 1.5) + win(25.3, 28.8, 0.1, 1.0))
mix += (hiss*0.03)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (10.0, 18.6, 24.6):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.25)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 5.0, 0.5)
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.0, 0.4)
for k, at in enumerate((11.3, 13.8, 16.6, 19.3, 21.6)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(10.0, 29.2, 1.5, 1.0)
mix += (pad*0.018)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 10.2), ("v3", 18.9), ("v4", 24.8), ("v6", 29.6),
      ("oA", 32.7), ("oB", 35.1), ("oC", 37.5), ("oD", 40.1), ("v7", 43.2))
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
