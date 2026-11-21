import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 50.5; N = int(SR*DUR)
rng = np.random.default_rng(20); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 29.0
w3d = win(0, E3, 0.8, 0.8)
# countryside: soft wind, birds, crickets
wind = filt(noise(N), 80, 700, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.09*t))
mix += (wind*0.045*w3d)[:, None]
for k in range(14):
    at = rng.uniform(0.5, 15); m = int(0.3*SR); y = np.arange(m)/SR
    f0 = rng.uniform(2500, 3800)
    put(np.sin(2*np.pi*(f0 + 600*np.sin(2*np.pi*9*y))*y)*np.exp(-y*9), at, 0.010, rng.uniform(-0.7, 0.7))
cri = np.sin(2*np.pi*4400*t)*(np.sin(2*np.pi*28*t) > 0.3)*(0.5 + 0.5*np.sin(2*np.pi*0.4*t))
mix += (cri*0.004*w3d)[:, None]
# train: horn in the distance, approaching rumble, the pass (16.1 .. 23.4), receding in D
T_PASS = 19.0
d = np.abs(22.0*(t - T_PASS)) + 3.0
loud = np.clip(12.0/d, 0, 1.0)*win(14.0, E3, 2.0, 0.8)
ramp = np.where(t < T_PASS, loud, np.maximum(loud, 0.85*win(T_PASS, 23.4, 0.05, 0.3)))
ramp = ramp*np.where(t >= 23.4, 0.12*np.clip(1 - (t - 23.4)/6, 0, 1)/np.maximum(ramp, 1e-3)*ramp + 0, 1)
rum = filt(noise(N), 25, 160)*1.6 + filt(noise(N), 160, 1200)*0.6
mix += (rum*0.10*ramp)[:, None]
# wheel clacks on rail joints/welds while the cars pass
for k in range(46):
    at = T_PASS - 0.2 + k*0.105 + (0.05 if k % 4 >= 2 else 0)
    if at > 23.3: break
    m = int(0.05*SR); y = np.arange(m)/SR
    put(filt(noise(m), 300, 4000)*np.exp(-y*80) + np.sin(2*np.pi*140*y)*np.exp(-y*60), at, 0.10, 0.2)
# horn (two tones) far away
hn = int(1.6*SR); y = np.arange(hn)/SR
horn = (np.sign(np.sin(2*np.pi*311*y)) + np.sign(np.sin(2*np.pi*370*y)))*np.clip(y/0.08, 0, 1)*np.clip((1.6 - y)/0.2, 0, 1)
put(filt(horn, 200, 2500)*0.5, 15.0, 0.035, -0.3)
# whoosh at the pass
m = int(1.2*SR); y = np.arange(m)/SR
put(filt(noise(m), 200, 4000)*np.sin(np.pi*y/1.2)**2, T_PASS - 0.6, 0.35)
n = int(1.0*SR); x = np.arange(n)/SR
for at in (9.9, 15.9, 23.4):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.2)
for k, at in enumerate((10.2, 11.6, 13.0, 17.8, 20.0, 21.0)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 26.0, 0.4)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(9.9, 28.8, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 10.1), ("v3", 16.1), ("v4", 23.6), ("v6", 29.3),
      ("oA", 32.6), ("oB", 35.6), ("oC", 38.0), ("oD", 40.8), ("v7", 43.8))
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
