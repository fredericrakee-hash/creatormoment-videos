import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.5; N = int(SR*DUR)
rng = np.random.default_rng(33); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
w3d = win(0, E3, 0.8, 0.8)
# open range: wind + idling tank engine (low rumble + faint turbine whine)
wind = filt(noise(N), 60, 900, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.13*t))
mix += (wind*0.05*w3d)[:, None]
eng = filt(noise(N), 25, 140)*(1 + 0.2*np.sin(2*np.pi*11*t)) + 0.15*np.sin(2*np.pi*3400*t)*filt(noise(N), 1, 6)
near = np.where((t > 17.6) & (t < 24.0), 0.6, 1.0)
mix += (eng*0.06*w3d*near)[:, None]
def boom(at, g=1.0):
    n = int(5.0*SR); x = np.arange(n)/SR
    crack = filt(noise(n), 800, 12000)*np.exp(-x*40)
    body = filt(noise(n), 20, 220, 4)*np.exp(-x*1.6)*6
    thump = np.sin(2*np.pi*(38 + 30*np.exp(-x*8))*x)*np.exp(-x*5)*1.5
    tail = filt(noise(n), 60, 500)*np.exp(-x*0.8)*np.clip(x/0.3, 0, 1)*1.2
    sig = crack*1.2 + body + thump + tail
    put(sig/np.max(np.abs(sig)), at, 0.75*g)
    m_ = int(0.5*SR); y = np.arange(m_)/SR      # breech / recoil clank
    clank = (np.sin(2*np.pi*310*y) + 0.7*np.sin(2*np.pi*870*y) + 0.4*np.sin(2*np.pi*1730*y))*np.exp(-y*14)
    put(clank, at + 0.9, 0.05*g)
for f in (3.0, 26.4): boom(f)
# pre-shot tension tick
for at in (1.9, 2.4, 25.3, 25.8):
    m_ = int(0.06*SR); y = np.arange(m_)/SR
    put(np.sin(2*np.pi*1500*y)*np.exp(-y*60), at, 0.05)
n = int(1.0*SR); x = np.arange(n)/SR
for at in (7.4, 17.6, 24.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.16)
for k, at in enumerate((1.6, 10.0, 13.6, 19.6, 27.6, 28.4)):
    m_ = int(0.25*SR); y = np.arange(m_)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(7.4, 30.8, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 7.6), ("v3", 17.8), ("v4", 24.2), ("v6", 31.3),
      ("oA", 34.1), ("oB", 36.4), ("oC", 39.0), ("oD", 41.6), ("v7", 44.4))
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
