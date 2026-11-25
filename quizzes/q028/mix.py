import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 52.0; N = int(SR*DUR)
rng = np.random.default_rng(28); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 31.6
w3d = win(0, E3, 0.8, 0.8)
# airfield wind + insects-free grass rustle
wind = filt(noise(N), 200, 3000)*(0.6 + 0.4*np.sin(2*np.pi*0.06*t))
mix += (wind*0.04*w3d)[:, None]
# jet: distance-based loudness from the camera, per shot
X0, V0 = 2400.0, 75.0
jx = X0 - V0*t
cam = np.where(t < 5.0, 1640.0, np.where(t < 13.6, 1525.0, np.where(t < 23.4, -1560.0, 0.0)))
dist = np.abs(jx - cam) + np.where(t < 5.0, 420.0, 25.0)
dist = np.where(t >= 23.4, 260.0, dist)
g = np.clip(60.0/dist, 0, 1.6)
g = np.where((t >= 13.6) & (t < 23.4), 0.05, g)          # other end of the runway: far away
roar = filt(noise(N), 60, 900)*1.3 + filt(noise(N), 900, 7000)*0.5
whine = np.sin(2*np.pi*np.cumsum(2200 + 300*np.tanh((cam - jx)/80.0))/SR)*0.15
mix += ((roar + whine)*0.08*g*w3d)[:, None]
# flyover in shot B: extra low thump + pan sweep around t ~ 11.7
m = int(3.0*SR); y = np.arange(m)/SR
fly = filt(noise(m), 40, 500)*np.exp(-((y - 1.2)/0.8)**2)
put(fly, 10.6, 0.5, pan=0.0)
# touchdown screech heard far away in D: reverse thrust rumble
rev = filt(noise(N), 50, 700)*win(23.4, 31.6, 0.6, 0.6)*np.clip(1 - (t - 23.4)/12, 0.3, 1)
mix += (rev*0.06)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (5.0, 13.6, 23.4):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.16)
for k, at in enumerate((2.4, 8.6, 10.6, 17.6, 19.8, 25.4)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(4.5, 31.4, 1.5, 1.0)
mix += (pad*0.015)[:, None]
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.4, 0.35)
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.4), ("v2", 5.2), ("v3", 13.9), ("v4", 23.7), ("v6", 31.9),
      ("oA", 34.8), ("oB", 37.9), ("oC", 40.2), ("oD", 42.5), ("v7", 45.3))
for n_, at in VO[5:9]:
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at-0.05, 0.12)
voice = np.zeros(N)
for n_, at in VO:
    v_ = load(n_); i = int(at*SR); j = min(N, i+len(v_)); voice[i:j] += v_[:j-i]
duck = 1 - 0.55*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
