import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 49.5; N = int(SR*DUR)
rng = np.random.default_rng(19); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 28.6
w3d = win(0, E3, 0.8, 0.8)
# mountain wind
wind = filt(noise(N), 80, 900, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.11*t) + 0.2*np.sin(2*np.pi*0.37*t))
mix += (wind*0.05*w3d)[:, None]
# truck: diesel rumble + tyre roar, loudness by shot (approach in A, chase in B, very close in C)
near = np.interp(t, [0, 9.6, 9.61, 15.4, 15.41, 18.0, 20.4, 21.4, 21.41, 28.6], [0.25, 1.0, 0.75, 0.85, 1.0, 1.0, 0.55, 0.35, 0.25, 0.2])
rpm = np.interp(t, [0, 15.6, 20.4, 28.6], [1.0, 1.08, 0.7, 0.6])
ph = np.cumsum(2*np.pi*38*rpm/SR)
eng = (np.sin(ph) + 0.6*np.sin(2*ph + 0.3) + 0.35*np.sin(3*ph) + 0.25*np.sign(np.sin(0.5*ph)))*(1 + 0.3*filt(noise(N), 2, 15))
eng = filt(eng, 30, 400)
mix += (eng*0.06*near*w3d)[:, None]
roll = filt(noise(N), 150, 1800)*np.clip(np.interp(t, [0, 15.6, 20.4], [1, 1, 0]), 0, 1)
mix += (roll*0.05*near*w3d)[:, None]
# hot brakes: hiss/squeal in A-B
sq = (np.sin(2*np.pi*(2400 + 60*np.sin(2*np.pi*0.7*t))*t)*0.4 + filt(noise(N), 3000, 7000))*win(1.0, 15.6, 1.5, 0.3)*(0.5 + 0.5*np.sin(2*np.pi*0.23*t)**2)
mix += (sq*0.012*near)[:, None]
# gravel: dense crunch/crackle while ploughing in (15.6 .. 20.4), fading with speed
v = np.clip(np.interp(t, [15.6, 20.4], [1.0, 0.0]), 0, 1)*(t >= 15.6)
cr = filt(noise(N), 400, 6000)*(np.abs(filt(noise(N), 20, 200))**1.5)*8
mix += (cr*0.05*v)[:, None]
mix += (filt(noise(N), 40, 300)*0.22*v)[:, None]
for k in range(260):
    at = rng.uniform(15.6, 20.6); m = int(0.02*SR); y = np.arange(m)/SR
    put(filt(noise(m), 1500, 9000)*np.exp(-y*250), at, 0.06*float(np.interp(at, [15.6, 20.6], [1, 0.1])), rng.uniform(-0.8, 0.8))
# impact at the gravel entry
m = int(1.5*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(55 - 15*y)*y)*np.exp(-y*3) + filt(noise(m), 200, 3000)*np.exp(-y*4)*0.6, 15.6, 0.55)
# settling stones in D
for k in range(40):
    at = rng.uniform(20.5, 27.0); m = int(0.03*SR); y = np.arange(m)/SR
    put(filt(noise(m), 2000, 8000)*np.exp(-y*200), at, 0.02, rng.uniform(-0.8, 0.8))
n = int(1.0*SR); x = np.arange(n)/SR
for at in (9.6, 15.4, 21.4):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.2)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.6, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(9.6, 28.4, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 9.8), ("v3", 15.6), ("v4", 21.6), ("v6", 28.9),
      ("oA", 31.4), ("oB", 34.0), ("oC", 37.2), ("oD", 39.6), ("v7", 42.4))
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
