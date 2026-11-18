import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 52.5; N = int(SR*DUR)
rng = np.random.default_rng(13); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
wA = win(0, 6.8, 0.4, 0.05); wB = win(6.8, 16.3, 0.05, 0.1); wC = win(16.3, 32.3, 0.1, 0.8)
# countryside wind
for ch in range(2):
    mix[:, ch] += filt(noise(N), 90, 1500)*(0.6+0.4*np.sin(2*np.pi*0.11*t+ch))*(0.06*wA + 0.06*wB)
# approaching train: rising rumble + whine (shot A)
appr = np.clip(t/6.8, 0, 1)**2
mix += ((filt(noise(N), 50, 500, 3)*0.5 + filt(noise(N), 800, 3000)*0.15)*appr*wA*0.6)[:, None]
# shot B: faint electric hum of the line
mix += ((np.sin(2*np.pi*100*t)*0.3 + np.sin(2*np.pi*200*t)*0.1 + filt(noise(N), 3000, 8000)*0.05)*wB*0.05)[:, None]
# shot C: slowed-down roof ride: deep rumble + airflow + soft wire hiss
mix += ((filt(noise(N), 30, 220, 3)*0.9 + filt(noise(N), 300, 2000)*0.25)*wC*0.22)[:, None]
for k in np.arange(16.6, 32.0, 1.35):
    m = int(0.5*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(45 - 10*y)*y)*np.exp(-y*7), k, 0.18)
hiss = filt(noise(N), 2500, 9000)*(0.6 + 0.4*np.sin(2*np.pi*t/3.7))
mix += (hiss*wC*0.025)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (6.8, 16.3):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
# hit on "no mistake"
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 27.5, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(16.3, 32.1, 1.5, 1.0)
mix += (pad*0.02)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-32.3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 32.3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 31.5, 0.12)
VO = (("v1", 0.3), ("v2", 7.0), ("v3", 16.6), ("v4", 27.5), ("v6", 32.5),
      ("oA", 35.0), ("oB", 37.4), ("oC", 40.2), ("oD", 42.7), ("v7", 46.0))
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
