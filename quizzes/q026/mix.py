import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 51.4; N = int(SR*DUR)
rng = np.random.default_rng(26); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
E3 = 32.2
w3d = win(0, E3, 0.8, 0.8)
# apron ambience: APU hum, distant jets taxiing, wind
amb = filt(noise(N), 60, 600, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.07*t))
mix += (amb*0.05*w3d)[:, None]
apu = np.sin(2*np.pi*400*t) + 0.5*np.sin(2*np.pi*800*t) + filt(noise(N), 300, 3000)*1.5
mix += (apu*0.006*w3d)[:, None]
far = filt(noise(N), 500, 4000)*np.clip(np.sin(2*np.pi*(t - 2)/26), 0, 1)**2
mix += (far*0.03*w3d)[:, None]
# engine start: starter whine rises, light-up rumble, then idle roar + fan whine
T0 = 13.3
sp = np.clip((t - T0)/4.5, 0, 1); sp = sp*sp*(3 - 2*sp)
on = (t > T0).astype(float)
dist = np.where(t >= 20.6, 0.45, 1.0)                     # D is 50 m away
f_wh = 300 + 2600*sp
ph = 2*np.pi*np.cumsum(f_wh)/SR
whine = (np.sin(ph) + 0.35*np.sin(2*ph))*on
mix += (whine*0.035*np.clip((t - T0)/1.0, 0, 1)*dist*w3d)[:, None]
lit = np.clip((t - 15.0)/1.2, 0, 1)
roar = filt(noise(N), 60, 700)*1.4 + filt(noise(N), 700, 6000)*0.6
mix += (roar*0.10*lit*(0.6 + 0.4*sp)*dist*w3d)[:, None]
m = int(1.5*SR); y = np.arange(m)/SR
put(filt(noise(m), 40, 400)*np.exp(-y*2.5)*np.clip(y/0.15, 0, 1), 15.0, 0.25)          # light-up whump
n = int(1.0*SR); x = np.arange(n)/SR
for at in (3.4, 12.9, 20.6):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.18)
for k, at in enumerate((4.6, 6.9, 15.6, 18.0, 23.2, 24.4)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 24.4, 0.35)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(3.4, 32.0, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 3.7), ("v3", 13.2), ("v4", 23.0), ("v6", 32.5),
      ("oA", 35.7), ("oB", 38.0), ("oC", 40.3), ("oD", 42.4), ("v7", 45.1))
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
