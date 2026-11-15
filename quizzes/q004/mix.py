import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 54.0; N = int(SR*DUR)
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
# A: takeoff roar building up, whine rising
sA = win(0, 12.5, 0.3, 0.1)
build = np.clip((t-0.3)/7.5, 0, 1)**1.3
roar = filt(noise(N), 40, 1200, 3)*(0.25 + 0.75*build)
whine_f = 900 + 1700*build
whine = np.sin(2*np.pi*np.cumsum(whine_f)/SR)*0.08*build
rumble = filt(noise(N), 20, 120)*0.8*build*(t < 8.4)          # wheels on runway
mix += ((roar*0.5 + whine + rumble*0.6)*sA)[:, None]
for at in (10.1, 11.7):
    m = int(0.6*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*60*y)*np.exp(-y*9) + filt(noise(m), 200, 1500)*np.exp(-y*20)*0.4, at, 0.35)
# B: in-flight roar + fire bell + alert voice
sB = win(12.5, 22.0, 0.1, 0.1); sC = win(22.0, 34.3, 0.1, 0.6)
flight = filt(noise(N), 60, 900, 3)*0.35 + filt(noise(N), 900, 4000)*0.06
mix += (flight*(sB + sC))[:, None]
for k in range(10):
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*1450*y)*np.exp(-y*25) + 0.5*np.sin(2*np.pi*2900*y)*np.exp(-y*30), 17.15 + k*0.17, 0.16)
v = filt(load("a_eng"), 400, 3000, 4); v = np.tanh(v*2.2)/np.tanh(2.2); put(v, 17.5, 0.32)
n = int(2.5*SR); x = np.arange(n)/SR
put(filt(noise(n), 200, 2500)*np.sin(np.pi*x/2.5)**2, 19.6, 0.18)
# cut whooshes
for at in (12.5, 22.0):
    n = int(1.0*SR); x = np.arange(n)/SR; put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.3)
# C: fuel-dump hiss rising
hiss = filt(noise(N), 2500, 11000)*np.clip((t-24.0)/3.0, 0, 1)
for ch, ph in ((0, 0.0), (1, 1.3)):
    mix[:, ch] += hiss*sC*0.07*(0.8+0.2*np.sin(2*np.pi*0.6*t+ph))
tens = (np.sin(2*np.pi*55*t) + 0.5*np.sin(2*np.pi*82.5*t))*win(13.0, 33.8, 2.0, 0.8)*0.04
mix += tens[:, None]
# quiz
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-34.6)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 34.6 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 33.8, 0.12)
for at in (37.75, 39.95, 42.05, 44.95):
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at, 0.12)
voice = np.zeros(N)
for n_, at in (("v1", 0.5), ("v2", 7.0), ("v3", 13.0), ("v4", 19.9), ("v5", 23.0), ("v6", 26.8), ("vq", 34.7),
               ("oA", 37.8), ("oB", 40.0), ("oC", 42.1), ("oD", 45.0), ("v7", 48.0)):
    v = load(n_); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
