import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.5; N = int(SR*DUR)
rng = np.random.default_rng(22); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 31.0
wA = win(0, 7.0, 0.4, 0.05); wB = win(7.0, 16.4, 0.05, 0.1); wC = win(16.4, E3, 0.1, 0.8)
TI, TL = 18.2, 20.4
for ch in range(2):
    mix[:, ch] += filt(noise(N), 100, 2000)*(0.6+0.4*np.sin(2*np.pi*0.11*t+ch))*(0.06*wA + 0.04*wB + 0.03*wC)
# venting hiss (louder in the close-up)
hiss = filt(noise(N), 1500, 9000)*(0.7 + 0.3*np.sin(2*np.pi*0.22*t))
mix += (hiss*np.clip((TL + 1 - t)/1.0, 0, 1)*(0.02*wA + 0.05*wB + 0.02*wC))[:, None]
# birds far away before launch
for k in range(8):
    at = rng.uniform(0.5, 15); m = int(0.3*SR); y = np.arange(m)/SR
    f0 = rng.uniform(2500, 3800)
    put(np.sin(2*np.pi*(f0 + 600*np.sin(2*np.pi*9*y))*y)*np.exp(-y*9), at, 0.008, rng.uniform(-0.7, 0.7))
for k in np.arange(16.5, 20.5, 1.0):
    m = int(0.08*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*1200*y)*np.exp(-y*50), k, 0.05)
n = int(1.2*SR); x = np.arange(n)/SR
for at in (7.0, 16.4, 22.5):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.25)
rum = filt(noise(N), 25, 220, 3)
kc = np.clip((t - TI)/0.8, 0, 1); kl = np.clip((t - TL)/0.4, 0, 1)
crack = filt(noise(N), 800, 6000)*(np.abs(filt(noise(N), 2, 18)) > 0.9)
roar = rum*(0.45*kc + 0.9*kl) + filt(noise(N), 150, 2500)*(0.12*kc + 0.35*kl) + crack*0.25*kl
fade = np.clip((E3 - 0.3 - t)/1.5, 0, 1)*(1 - 0.35*np.clip((t - 26)/3, 0, 1))
mix += (roar*fade*wC)[:, None]
m = int(2.5*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(45 - 10*y)*y)*np.exp(-y*1.2) + filt(noise(m), 60, 400)*np.exp(-y*1.5)*0.6, TL, 0.6)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 25.9, 0.3)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(7.0, 30.6, 2.0, 1.0)
mix += (pad*0.02)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 7.2), ("v3", 16.7), ("v4", 25.8), ("v6", 31.3),
      ("oA", 34.0), ("oB", 36.6), ("oC", 39.0), ("oD", 41.4), ("v7", 44.3))
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
