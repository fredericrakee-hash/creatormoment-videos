import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 49.5; N = int(SR*DUR)
rng = np.random.default_rng(15); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
w3d = win(0, 28.2, 0.8, 0.8)
# arctic wind + low ship engine/propeller rumble
wind = filt(noise(N), 200, 1500, 2)*(0.6 + 0.4*np.sin(2*np.pi*0.13*t))
mix += (wind*0.05*w3d)[:, None]
rumble = filt(noise(N), 25, 120, 3)*2.0 + np.sin(2*np.pi*42*t)*0.3 + np.sin(2*np.pi*63*t + 1)*0.15
mix += (rumble*(0.06*w3d + 0.05*win(7.4, 14.6, 0.1, 0.1)))[:, None]
# ice cracking: deep thuds + sharp cracks + grinding, denser on the close shots
def crack(at, g, pan):
    m = int(0.5*SR); y = np.arange(m)/SR
    thud = np.sin(2*np.pi*(70 - 30*y)*y)*np.exp(-y*9)
    snap = filt(noise(m), 1500, 9000)*np.exp(-y*40)*rng.uniform(0.3, 0.9)
    put(thud + snap, at, g, pan)
for k in range(60):
    at = rng.uniform(0.5, 28.0); close = 7.4 <= at < 21.0
    crack(at, rng.uniform(0.08, 0.25)*(1.6 if close else 0.6), rng.uniform(-0.5, 0.5))
grind = filt(noise(N), 300, 2500, 2)*(0.5 + 0.5*np.abs(np.sin(2*np.pi*0.7*t)))
mix += (grind*0.035*win(7.4, 21.0, 0.2, 0.2))[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (7.4, 14.6, 21.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.25)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 22.0, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(14.6, 28.0, 1.5, 1.0)
mix += (pad*0.018)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-28.2)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 28.2 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 27.4, 0.12)
VO = (("v1", 0.3), ("v2", 7.6), ("v3", 14.8), ("v4", 21.2), ("v6", 28.4),
      ("oA", 31.7), ("oB", 34.5), ("oC", 37.5), ("oD", 40.1), ("v7", 42.9))
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
