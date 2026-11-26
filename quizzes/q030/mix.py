import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 48.5; N = int(SR*DUR)
rng = np.random.default_rng(30); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 28.8
w3d = win(0, E3, 0.8, 0.8)
# cold winter wind, howling a little
wind = filt(noise(N), 100, 1200, 2)*(0.6 + 0.4*np.sin(2*np.pi*0.13*t))
howl = np.sin(2*np.pi*(420 + 60*np.sin(2*np.pi*0.2*t))*t)*0.15
mix += ((wind*0.05 + filt(howl, 300, 700)*0.02)*w3d)[:, None]
# city hum far away
mix += (filt(noise(N), 40, 160)*0.03*w3d)[:, None]
# burners: whoomp as each section lights (wave 9.3..10.5), then a steady gas roar with flicker
TI = 9.3
for k in range(6):
    m = int(0.6*SR); y = np.arange(m)/SR
    put(filt(noise(m), 60, 1500)*np.exp(-y*6)*np.clip(y/0.02, 0, 1), TI + k*0.18, 0.18, -0.4 + 0.15*k)
roar = filt(noise(N), 80, 2500)*(0.8 + 0.2*np.sin(2*np.pi*7*t)*np.sin(2*np.pi*2.3*t))
gr = np.clip((t - TI)/1.2, 0, 1)
gain = np.where((t > 14.9) & (t < 20.0), 0.07, np.where(t < 14.9, 0.12, 0.05))
mix += (roar*gr*gain*w3d)[:, None]
crk = (rng.random(N) < 0.0015).astype(float)*rng.standard_normal(N)
mix += (filt(crk, 2000, 9000)*0.12*gr*w3d)[:, None]
# commuter train: horn far away at 3.0, approach rumble, pass-by roar ~17.6, clacks over the junction, fading after
hn = int(1.6*SR); y = np.arange(hn)/SR
horn = (np.sign(np.sin(2*np.pi*349*y)) + np.sign(np.sin(2*np.pi*440*y)) + np.sign(np.sin(2*np.pi*523*y)))*np.clip(y/0.08, 0, 1)*np.clip((1.6 - y)/0.25, 0, 1)
put(filt(horn, 250, 2500)*0.5, 3.0, 0.03, 0.3)
put(filt(horn, 250, 2500)*0.5, 15.4, 0.10, 0.2)
d_tr = np.abs(8.0 + 14.0*(17.6 - t) + 10.0)
rum = filt(noise(N), 30, 600)*(1.0/(1.0 + (d_tr/25.0)**2))
mix += (rum*0.45*win(0, E3, 0.5, 0.8))[:, None]
k = 0; tt_ = 16.6
while tt_ < 26.0:
    m = int(0.05*SR); y = np.arange(m)/SR
    put(filt(noise(m), 300, 4000)*np.exp(-y*80) + np.sin(2*np.pi*140*y)*np.exp(-y*60), tt_, 0.12 if tt_ < 20 else 0.05, -0.2)
    tt_ += 0.12 if k % 2 == 0 else (13.0/14.0); k += 1
n = int(1.0*SR); x = np.arange(n)/SR
for at in (6.6, 14.9, 20.0):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.18)
for k, at in enumerate((2.4, 4.0, 7.4, 10.6, 16.0, 21.4, 24.6)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(6.6, 28.6, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 6.8), ("v3", 15.0), ("v4", 20.1), ("v6", 29.0),
      ("oA", 32.0), ("oB", 34.7), ("oC", 37.5), ("oD", 39.8), ("v7", 42.4))
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
