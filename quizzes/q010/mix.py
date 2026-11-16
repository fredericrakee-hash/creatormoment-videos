import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 44.0; N = int(SR*DUR)
rng = np.random.default_rng(10); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
wA = win(0, 5.2, 0.4, 0.05); wB = win(5.2, 13.4, 0.05, 0.1); wC = win(13.4, 25.6, 0.1, 0.8)
# wind + distant traffic hum
for ch in range(2):
    mix[:, ch] += filt(noise(N), 90, 1800)*(0.6+0.4*np.sin(2*np.pi*0.13*t+ch))*(0.07*wA + 0.05*wB + 0.03*wC)
mix += (filt(noise(N), 60, 700, 3)*(0.10*wA + 0.16*wB))[:, None]
# pass-bys in shot B
def passby(at, g, dur=2.2, pan=0.0):
    n = int(dur*SR); x = np.arange(n)/SR; env = np.exp(-((x - dur/2)/(dur/5))**2)
    put(filt(noise(n), 150, 4000)*env, at - dur/2, g, pan)
for at, g in ((7.95, 0.55), (11.5, 0.65), (6.3, 0.18), (9.8, 0.2), (12.6, 0.18)):
    passby(at, g)
# joint thunks: hero car axles + truck axles + background
def thunk(at, g):
    m = int(0.35*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(70 - 30*y)*y)*np.exp(-y*16) + filt(noise(m), 300, 3000)*np.exp(-y*40)*0.5, at, g)
for at in (7.944, 8.056): thunk(at, 0.75)
for at in (11.30, 11.457, 11.819, 11.886): thunk(at, 0.85)
for at in (6.1, 6.25, 9.4, 9.52, 10.4, 10.55, 12.9, 13.05): thunk(at, 0.15)
n = int(1.0*SR); x = np.arange(n)/SR
for at in (5.2, 13.4):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
# time-lapse: ticking clock + slow metal groan as the teeth slide
for k in np.arange(13.6, 25.4, 0.25):
    m = int(0.03*SR); y = np.arange(m)/SR
    put(filt(noise(m), 2500, 8000)*np.exp(-y*120), k, 0.12)
groan = np.sin(2*np.pi*(90 + 25*np.sin(2*np.pi*t/5.6))*t)*0.6 + filt(noise(N), 120, 600)*0.4
mix += (groan*wC*0.05)[:, None]
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 20.6, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(13.4, 25.2, 1.5, 1.0)
mix += (pad*0.022)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-25.6)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 25.6 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 24.8, 0.12)
VO = (("v1", 0.3), ("v2", 5.4), ("v3", 13.7), ("v4", 20.6), ("v6", 25.8),
      ("oA", 28.1), ("oB", 30.6), ("oC", 33.0), ("oD", 35.2), ("v7", 37.1))
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
