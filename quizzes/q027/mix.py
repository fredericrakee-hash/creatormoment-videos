import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 53.5; N = int(SR*DUR)
rng = np.random.default_rng(27); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 33.2
w3d = win(0, E3, 0.8, 0.8)
# open sea: swell wash (slow amplitude modulation), wind, gulls-free
wash = filt(noise(N), 150, 2500, 2)*(0.55 + 0.45*np.sin(2*np.pi*0.18*t)**2)
mix += (wash*0.07*w3d)[:, None]
wind = filt(noise(N), 400, 5000)*(0.6 + 0.4*np.sin(2*np.pi*0.05*t + 1))
mix += (wind*0.025*w3d)[:, None]
lap = filt(noise(N), 300, 3000)*np.clip(np.sin(2*np.pi*0.6*t), 0, 1)**3      # water slapping the hull, close shots
mix += (lap*0.06*win(5.0, 23.6, 0.3, 0.3))[:, None]
# surfacing: deep rush of water + low rumble (shot A)
m = int(4.5*SR); y = np.arange(m)/SR
rush = filt(noise(m), 80, 1800)*np.sin(np.pi*np.clip(y/4.5, 0, 1))**1.5
put(rush, 0.3, 0.22)
put(filt(noise(m), 25, 120)*np.sin(np.pi*np.clip(y/4.5, 0, 1)), 0.3, 0.35)
# low submarine hum in the close shots
hum = np.sin(2*np.pi*55*t) + 0.5*np.sin(2*np.pi*110*t)
mix += (hum*0.012*win(5.0, 23.6, 0.6, 0.6))[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (5.0, 14.0, 23.6):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.16)
for k, at in enumerate((7.2, 8.6, 15.6, 18.6, 25.6, 29.0)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
# sonar-free ominous pad (no ping: would give the answer away)
pad = (np.sin(2*np.pi*73.4*t) + np.sin(2*np.pi*110*t) + 0.6*np.sin(2*np.pi*146.8*t))*win(4.5, 33.0, 1.5, 1.0)
mix += (pad*0.016)[:, None]
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.6, 0.35)
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.4), ("v2", 5.2), ("v3", 14.3), ("v4", 24.0), ("v6", 33.5),
      ("oA", 37.0), ("oB", 39.3), ("oC", 41.6), ("oD", 43.9), ("v7", 46.9))
for n_, at in VO[5:9]:
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at-0.05, 0.12)
voice = np.zeros(N)
for n_, at in VO:
    v_ = load(n_); i = int(at*SR); j = min(N, i+len(v_)); voice[i:j] += v_[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
