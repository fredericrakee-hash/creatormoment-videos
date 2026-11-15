import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 45.4; N = int(SR*DUR)
rng = np.random.default_rng(5); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
wA = win(0, 9.0, 0.5, 0.05); wB = win(9.0, 29.6, 0.05, 0.8)
# countryside wind + a few birds
for ch in range(2):
    mix[:, ch] += filt(noise(N), 80, 1200)*(0.6+0.4*np.sin(2*np.pi*0.13*t+ch))*(wA+wB*0.5)*0.05
for _ in range(9):
    at = rng.uniform(0.5, 28); m = int(0.18*SR); y = np.arange(m)/SR; f0 = rng.uniform(2800, 4200)
    put(np.sin(2*np.pi*(f0 + 900*np.sin(2*np.pi*14*y))*y)*np.sin(np.pi*y/0.18)**2, at, 0.025, pan=rng.uniform(-0.8, 0.8))
# approaching train (shot A): rumble growing as it comes closer
appr = np.clip(t/9.0, 0, 1)**2.2
rum = filt(noise(N), 30, 260, 3)
mix += (rum*wA*(0.05 + 0.5*appr))[:, None]
hiss = filt(noise(N), 1500, 7000)
mix += (hiss*wA*0.08*appr)[:, None]
# wheel / rail clicks (rail joints) – A: fast, B: slow and close
def clicks(t0, t1, period, g, lp=2500):
    k = t0
    while k < t1:
        for dd in (0.0, 0.11):
            m = int(0.08*SR); y = np.arange(m)/SR
            put(filt(noise(m), 200, lp)*np.exp(-y*60) + np.sin(2*np.pi*95*y)*np.exp(-y*40), k+dd, g)
        k += period
clicks(5.5, 9.0, 0.55, 0.22)
clicks(9.4, 29.4, 1.6, 0.35)
mix += (rum*wB*0.32)[:, None]
# faint flange squeal in the curve, then it calms down once the axle has shifted
sq = np.sin(2*np.pi*(2350 + 30*np.sin(2*np.pi*0.7*t))*t)*filt(noise(N), 1, 6)*0.0 + np.sin(2*np.pi*2350*t)
mix += (sq*win(12.0, 21.5, 1.5, 1.2)*0.012)[:, None]
# whoosh into close-up, blips for overlays
n = int(1.0*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*np.exp(-x*3), 9.0, 0.3)
for at in (10.4, 11.2, 15.8, 19.7, 21.9, 23.2):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(520 + 300*y/0.25)*y)*np.exp(-y*12), at, 0.12)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 26.4, 0.4)
pad = (np.sin(2*np.pi*110*t) + np.sin(2*np.pi*164.8*t) + 0.6*np.sin(2*np.pi*220*t))*win(14.5, 29.0, 1.5, 1.0)
mix += (pad*0.025)[:, None]
# quiz bed + ticks
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-29.6)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 29.6 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 28.8, 0.12)
for at in (31.55, 33.55, 35.95, 37.75):
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at, 0.12)
voice = np.zeros(N)
for n_, at in (("v1", 0.3), ("v2", 9.2), ("v3", 14.5), ("v4", 19.6), ("v6", 29.8),
               ("oA", 31.6), ("oB", 33.6), ("oC", 36.0), ("oD", 37.8), ("v7", 39.5)):
    v = load(n_); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
