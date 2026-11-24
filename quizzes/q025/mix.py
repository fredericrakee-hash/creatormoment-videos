import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 51.0; N = int(SR*DUR)
rng = np.random.default_rng(25); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
# damp morning: soft wind, a few birds
wind = filt(noise(N), 80, 700, 2)*(0.7 + 0.3*np.sin(2*np.pi*0.09*t))
mix += (wind*0.04*w3d)[:, None]
for k in range(10):
    at = rng.uniform(0.5, 7); m = int(0.3*SR); y = np.arange(m)/SR
    f0 = rng.uniform(2500, 3800)
    put(np.sin(2*np.pi*(f0 + 600*np.sin(2*np.pi*9*y))*y)*np.exp(-y*9), at, 0.008, rng.uniform(-0.7, 0.7))
# diesel engine: idle -> throttle up at 8.0 (louder in the wide shots, muffled in close-ups)
thr = np.clip((t - 7.9)/1.5, 0, 1)
f_eng = 28 + 22*thr
ph = 2*np.pi*np.cumsum(f_eng)/SR
eng = (np.sign(np.sin(ph))*0.5 + np.sin(2*ph)*0.4 + np.sin(3*ph)*0.2)
eng = filt(eng, 20, 400) + filt(noise(N), 60, 900)*(0.3 + 0.7*thr)
gain_e = (0.10 + 0.12*thr)*w3d
mix += (eng*gain_e)[:, None]
# wheel slip: metallic squeal + fast rumble while the wheels spin (8.6 .. 21.6)
sl = np.clip((t - 8.6)/0.8, 0, 1)*np.clip((21.6 - t)/0.4, 0, 1)
sq = np.sin(2*np.pi*(2300 + 120*np.sin(2*np.pi*0.7*t))*t) + 0.5*np.sin(2*np.pi*3450*t)
mix += ((sq*0.010 + filt(noise(N), 150, 1500)*0.07*(0.6 + 0.4*np.sin(2*np.pi*13*t)))*sl)[:, None]
# air blast through the pipes (17.5 .. 23.6)
bl = np.clip((t - 17.45)/0.08, 0, 1)*np.clip((23.6 - t)/0.3, 0, 1)
mix += ((filt(noise(N), 1500, 9000)*0.10 + filt(noise(N), 300, 1500)*0.04)*bl)[:, None]
# grains hitting the rail: fine crackle
cr = (rng.random(N) < 0.004).astype(float)*rng.standard_normal(N)
mix += (filt(cr, 2000, 10000)*0.18*bl)[:, None]
# train starts rolling (21.6 ..): clacks over rail joints accelerating, couplers taking up slack
for k in range(9):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(filt(noise(m), 100, 2500)*np.exp(-y*20) + np.sin(2*np.pi*90*y)*np.exp(-y*15), 22.2 + k*0.32, 0.12*(1 - k/12), 0.3)
xpos = 0.0; k = 0
tt_ = 22.0
while tt_ < E3:
    v = max(0.3, 0.42*(tt_ - 21.6))
    m = int(0.05*SR); y = np.arange(m)/SR
    put(filt(noise(m), 300, 4000)*np.exp(-y*80) + np.sin(2*np.pi*140*y)*np.exp(-y*60), tt_, 0.07, -0.2)
    tt_ += 18.0/v/4 if k % 2 == 0 else 0.12
    k += 1
# horn at the start of D
hn = int(1.4*SR); y = np.arange(hn)/SR
horn = (np.sign(np.sin(2*np.pi*311*y)) + np.sign(np.sin(2*np.pi*370*y)))*np.clip(y/0.08, 0, 1)*np.clip((1.4 - y)/0.2, 0, 1)
put(filt(horn, 200, 2500)*0.5, 24.0, 0.05, -0.2)
n = int(1.0*SR); x = np.arange(n)/SR
for at in (7.4, 14.9, 23.5):
    put(filt(noise(n), 300, 5000)*np.exp(-x*3), at, 0.18)
for k, at in enumerate((3.2, 4.8, 8.2, 10.4, 16.0, 17.9, 21.9)):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(1200 + 80*k)*y)*np.exp(-y*18), at, 0.03)
# warning beeps for the slip display
for k in range(10):
    m = int(0.09*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*1650*y)*np.clip((0.09 - y)/0.02, 0, 1), 8.9 + k*0.8, 0.02)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 21.7, 0.35)
pad = (np.sin(2*np.pi*98*t) + np.sin(2*np.pi*146.8*t) + 0.6*np.sin(2*np.pi*196*t))*win(7.4, 31.3, 1.5, 1.0)
mix += (pad*0.015)[:, None]
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-E3)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), E3 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), E3 - 0.8, 0.12)
VO = (("v1", 0.3), ("v2", 7.7), ("v3", 15.1), ("v4", 21.6), ("v6", 31.8),
      ("oA", 35.4), ("oB", 37.7), ("oC", 40.0), ("oD", 42.3), ("v7", 44.7))
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
