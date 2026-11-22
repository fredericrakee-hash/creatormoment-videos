import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.5; N = int(SR*DUR)
rng = np.random.default_rng(21); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 31.4
w3d = win(0, E3, 0.8, 0.8)
harbor = win(0, 23.0, 0.8, 0.4); sea = win(23.0, E3, 0.4, 0.8)
# harbour: wind + water lapping against the hull
wind = filt(noise(N), 80, 700, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.09*t))
mix += (wind*0.04*w3d)[:, None]
lap = filt(noise(N), 150, 1400)*(0.5 + 0.5*np.sin(2*np.pi*0.45*t)**2)
mix += (lap*0.05*harbor*(1 + 0.6*win(9.0, 23.0, 0.2, 0.2)))[:, None]
# gulls
for k in range(9):
    at = rng.uniform(0.5, 22); m = int(0.5*SR); y = np.arange(m)/SR
    f0 = rng.uniform(1300, 1900)
    put(np.sin(2*np.pi*(f0 - 500*y)*y + 3*np.sin(2*np.pi*7*y))*np.exp(-y*5)*np.clip(y/0.03, 0, 1), at, 0.012, rng.uniform(-0.8, 0.8))
# crane: hum, reverse beeps, container landing clank at ~8.5 s
hum = filt(noise(N), 60, 200)*1.0
mix += (hum*0.03*win(0.2, 9.0, 0.6, 0.3))[:, None]
for k in range(6):
    m = int(0.18*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*1050*y)*np.clip(y/0.01, 0, 1)*np.clip((0.18-y)/0.01, 0, 1), 1.5 + k*0.9, 0.012, 0.5)
m = int(1.2*SR); y = np.arange(m)/SR
put((filt(noise(m), 80, 900)*np.exp(-y*9) + np.sin(2*np.pi*70*y)*np.exp(-y*6)), 8.4, 0.25)
# time-lapse whoosh (C) and deep metal groan as the hull settles
m = int(7.0*SR); y = np.arange(m)/SR
put(filt(noise(m), 40, 160)*np.sin(np.pi*y/7.0)**2, 15.4, 0.08)
put(np.sin(2*np.pi*(48 + 6*np.sin(2*np.pi*0.3*y))*y)*np.sin(np.pi*y/7.0)**2, 15.4, 0.05)
# open sea + ship horn (D)
surf = filt(noise(N), 100, 2500)*(0.6 + 0.4*np.sin(2*np.pi*0.18*t))
mix += (surf*0.06*sea)[:, None]
hn = int(2.4*SR); y = np.arange(hn)/SR
horn = (np.sin(2*np.pi*98*y) + 0.6*np.sin(2*np.pi*196*y) + 0.3*np.sin(2*np.pi*294*y))*np.clip(y/0.15, 0, 1)*np.clip((2.4-y)/0.4, 0, 1)
put(filt(horn, 60, 1500), 24.0, 0.10, -0.2)
# transitions
n = int(1.0*SR); x = np.arange(n)/SR
for at in (9.0, 14.8, 23.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.2)
for k, at in enumerate((1.5, 4.0, 9.4, 11.4, 15.0, 23.6)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 27.6, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(9.0, 31.0, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 9.2), ("v3", 15.0), ("v4", 23.4), ("v6", 31.6),
      ("oA", 34.2), ("oB", 36.6), ("oC", 39.1), ("oD", 41.4), ("v7", 44.4))
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
