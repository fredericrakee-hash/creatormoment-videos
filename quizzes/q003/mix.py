import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
SR = 44100; DUR = 42.8; N = int(SR*DUR)
rng = np.random.default_rng(4); mix = np.zeros((N, 2)); t = np.arange(N)/SR
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
above = np.maximum(win(0, 7.4, 1.0, 0.1), win(12.0, 28.0, 0.1, 0.6))
under = win(7.4, 12.0, 0.1, 0.1)
# sea + wind above water
for ch in range(2):
    sea = filt(noise(N), 120, 2500)*(0.55 + 0.45*np.sin(2*np.pi*0.18*t + ch*1.7))
    mix[:, ch] += sea*above*0.09
spray = filt(noise(N), 1500, 9000)*(0.5+0.5*np.sin(2*np.pi*0.4*t)**2)
mix += (spray*above*0.035)[:, None]
# big diesel engine hum (low, slow beat)
eng = (np.sin(2*np.pi*31*t) + 0.6*np.sin(2*np.pi*62.3*t) + 0.3*np.sin(2*np.pi*93*t))*(0.8+0.2*np.sin(2*np.pi*1.7*t))
mix += (eng*above*0.07 + eng*under*0.11)[:, None]
# dive: splash + bubbles, muffled underwater bed
n = int(1.2*SR); x = np.arange(n)/SR
put(filt(noise(n), 200, 6000)*np.exp(-x*3.5), 7.15, 0.5)
uw = filt(noise(N), 40, 350, 3)*under
mix += (uw*0.25)[:, None]
for _ in range(70):
    at = rng.uniform(7.4, 12.0); m = int(0.05*SR); y = np.arange(m)/SR; f = rng.uniform(300, 900)
    put(np.sin(2*np.pi*(f + 1800*y)*y)*np.exp(-y*60), at, 0.05, pan=rng.uniform(-0.7, 0.7))
# whoosh at the B->C cut
n = int(1.0*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*np.exp(-x*3), 12.0, 0.3)
# explanatory blips when the waves appear + stat hit
for at in (12.9, 16.6, 18.6):
    m = int(0.25*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(520 + 300*y/0.25)*y)*np.exp(-y*12), at, 0.12)
m = int(1.2*SR); y = np.arange(m)/SR
put(np.sin(2*np.pi*(60 - 15*y)*y)*np.exp(-y*4) + filt(noise(m), 2000, 8000)*np.exp(-y*14)*0.3, 23.9, 0.4)
# soft cinematic pad under the explanation
pad = (np.sin(2*np.pi*110*t) + np.sin(2*np.pi*164.8*t) + 0.6*np.sin(2*np.pi*220*t))*win(12.4, 27.6, 1.5, 1.0)
mix += (pad*0.025)[:, None]
# quiz bed + ticks
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-28.2)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 28.2 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 27.4, 0.12)
for at in (30.95, 32.65, 33.95, 35.25):
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at, 0.12)
voice = np.zeros(N)
for n_, at in (("v1", 0.3), ("v2", 7.8), ("v3", 12.2), ("v4", 21.5), ("v6", 28.3),
               ("oA", 31.0), ("oB", 32.7), ("oC", 34.0), ("oD", 35.3), ("v7", 36.8)):
    v = load(n_); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]; mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR); print("ok")
