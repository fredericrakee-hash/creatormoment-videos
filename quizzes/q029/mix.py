import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 53.3; N = int(SR*DUR)
rng = np.random.default_rng(29); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 33.5
w3d = win(0, E3, 0.8, 0.8)
# steppe wind, stronger gusts
wind = filt(noise(N), 60, 900, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.11*t))
mix += (wind*0.06*w3d)[:, None]
# parachute fabric flutter (A/B), muffled
fl = filt(noise(N), 80, 400)*(0.6 + 0.4*np.abs(np.sin(2*np.pi*1.7*t)))*win(0, 21.8, 0.5, 0.3)
mix += (fl*0.05)[:, None]
# recovery helicopter rotor in the distance (B)
rot = (np.sin(2*np.pi*5.2*t) > 0.6).astype(float)*filt(noise(N), 60, 300)
mix += (filt(rot, 40, 400)*0.10*win(8.8, 17.6, 0.3, 0.3))[:, None]
mix += (filt(rot, 40, 400)*0.03*win(17.6, E3, 0.3, 1.0))[:, None]
# soft-landing motors: sharp bang + roar (21.6), touchdown thud (21.82), dust hiss
TF = 21.6
m = int(1.6*SR); y = np.arange(m)/SR
put(filt(noise(m), 60, 6000)*np.exp(-y*5)*np.clip(y/0.005, 0, 1), TF, 0.9)
put(np.sin(2*np.pi*(55 - 20*y)*y)*np.exp(-y*3), TF, 0.7)
m = int(0.9*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(42 - 12*y)*y)*np.exp(-y*6) + filt(noise(m), 40, 500)*np.exp(-y*8)*0.6, TF + 0.22, 0.8)
hs = filt(noise(N), 800, 6000)*np.clip((t - TF)/0.05, 0, 1)*np.exp(-np.clip(t - TF, 0, None)/2.2)*(t > TF)
mix += (hs*0.06)[:, None]
# grass fire crackle (D)
cr = (rng.random(N) < 0.002).astype(float)*rng.standard_normal(N)
mix += ((filt(cr, 1500, 9000)*0.25 + filt(noise(N), 100, 900)*0.02)*win(25.4, E3, 1.0, 0.8))[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (8.8, 17.6, 25.7):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.18)
for k, at in enumerate((3.6, 5.6, 9.4, 12.0, 18.0, 22.0, 30.0)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(8.8, 33.3, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 9.0), ("v3", 17.7), ("v4", 25.9), ("v6", 33.8),
      ("oA", 37.2), ("oB", 39.5), ("oC", 42.1), ("oD", 44.7), ("v7", 47.2))
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
