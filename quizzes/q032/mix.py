import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.8; N = int(SR*DUR)
rng = np.random.default_rng(32); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 31.5
w3d = win(0, E3, 0.8, 0.8)
# harbour wind + distant industrial rumble
wind = filt(noise(N), 60, 900, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.11*t))
mix += (wind*0.05*w3d)[:, None]
mix += (filt(noise(N), 30, 160)*0.08*w3d)[:, None]
# gulls
for at in (1.2, 4.9, 9.8, 13.5, 26.0, 29.2):
    for j in range(3):
        m_ = int(0.22*SR); y = np.arange(m_)/SR
        f = 1700 + 500*np.sin(np.pi*y/0.22) - 300*y/0.22
        put(np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*y/0.22)**2*(0.5 + 0.5*np.sin(2*np.pi*35*y)), at + j*0.28, 0.025, pan=rng.uniform(-0.7, 0.7))
# distant metal clangs
for at in (3.3, 7.2, 11.9, 27.8):
    m_ = int(1.5*SR); y = np.arange(m_)/SR
    put((np.sin(2*np.pi*520*y) + 0.6*np.sin(2*np.pi*1310*y) + 0.4*np.sin(2*np.pi*2210*y))*np.exp(-y*3), at, 0.02, pan=rng.uniform(-0.5, 0.5))
# compressor hum + paint spray hiss (C)
wc = win(16.0, 23.9, 0.2, 0.2)
mix += ((np.sin(2*np.pi*60*t) + 0.5*np.sin(2*np.pi*120*t))*0.02*wc)[:, None]
mix += (filt(noise(N), 1500, 9000)*0.09*wc*(0.8 + 0.2*np.sin(2*np.pi*0.7*t)))[:, None]
n = int(1.0*SR); x = np.arange(n)/SR
for at in (8.6, 16.0, 23.9):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.18)
for k, at in enumerate((2.2, 4.2, 10.4, 12.2, 18.5, 24.3, 28.4)):
    m_ = int(0.25*SR); y = np.arange(m_)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(8.6, 31.3, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 8.8), ("v3", 16.2), ("v4", 24.1), ("v6", 31.8),
      ("oA", 34.9), ("oB", 37.1), ("oC", 39.5), ("oD", 42.1), ("v7", 44.6))
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
