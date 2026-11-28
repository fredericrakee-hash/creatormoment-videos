import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 49.2; N = int(SR*DUR)
rng = np.random.default_rng(34); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 30.6
w3d = win(0, E3, 0.8, 0.8)
# thin Martian wind + rover motors (soft whine) + gravel crunch
wind = filt(noise(N), 150, 1800, 2)*(0.6 + 0.4*np.sin(2*np.pi*0.09*t))
mix += (wind*0.035*w3d)[:, None]
motor = (np.sin(2*np.pi*620*t) + 0.5*np.sin(2*np.pi*1240*t + 0.4))*(0.8 + 0.2*np.sin(2*np.pi*0.5*t))
near = np.where((t > 7.8) & (t < 16.0), 1.0, 0.45)
mix += (motor*0.006*w3d*near)[:, None]
crunch = filt(noise(N), 400, 4000)*(rng.random(N) < 0.002)
mix += (np.convolve(crunch, np.exp(-np.arange(400)/60), mode="same")*0.05*w3d*near)[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (7.8, 16.0, 24.3):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.16)
for k, at in enumerate((1.4, 3.2, 9.6, 12.2, 19.0, 21.5, 24.7, 27.6)):
    m_ = int(0.25*SR); y = np.arange(m_)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(0.5, 30.4, 2.0, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 8.0), ("v3", 16.2), ("v4", 24.5), ("v6", 30.9),
      ("oA", 33.4), ("oB", 35.8), ("oC", 38.0), ("oD", 40.5), ("v7", 43.1))
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
