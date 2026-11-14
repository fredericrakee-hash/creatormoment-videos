import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 44100; DUR = 44.2; N = int(SR*DUR); CUT = 19.0
rng = np.random.default_rng(3)
mix = np.zeros((N, 2)); t = np.arange(N)/SR
A = QDIR + "/audio/"

def load(name):
    a, sr = sf.read(A+name+".wav")
    if a.ndim > 1: a = a.mean(1)
    a = resample_poly(a, SR, sr); return a/np.max(np.abs(a))
def put(sig, at, gain=1.0, pan=0.0):
    i = int(at*SR); j = min(N, i+len(sig)); s = sig[:j-i]*gain
    mix[i:j, 0] += s*(1-max(0, pan)); mix[i:j, 1] += s*(1+min(0, pan))
def filt(sig, lo=None, hi=None, order=2):
    if lo and hi: sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    elif lo: sos = butter(order, lo, btype="high", fs=SR, output="sos")
    else: sos = butter(order, hi, btype="low", fs=SR, output="sos")
    return sosfilt(sos, sig)
def win(a, b, fi=0.5, fo=0.5):
    return np.clip((t-a)/fi, 0, 1)*np.clip((b-t)/fo, 0, 1)
def noise(n): return rng.standard_normal(n)

# --- shot A: thin-air wind rush + tension drone
wa = win(0, CUT, 1.0, 0.05)
for ch in range(2):
    w = filt(noise(N), 250, 3000); mix[:, ch] += w*(0.6+0.4*np.sin(2*np.pi*0.2*t+ch))*wa*0.09
drone = np.sin(2*np.pi*41*t) + 0.5*np.sin(2*np.pi*61.5*t) + 0.2*np.sin(2*np.pi*82*t)
mix += (drone*(0.05 + 0.06*np.clip((t-8)/10, 0, 1))*wa)[:, None]
# fin deploy: hydraulic whir + clunks
n = int(1.6*SR); x = np.arange(n)/SR
whir = np.sin(2*np.pi*(180+140*x)*x)*0.4 + filt(noise(n), 300, 2000)*0.5
put(whir*np.hanning(n), 8.6, 0.12)
for k, at in enumerate((10.0, 10.12, 10.25, 10.4)):
    m = int(0.35*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*70*y)*np.exp(-y*14) + filt(noise(m), 800, 5000)*np.exp(-y*40)*0.5), at, 0.35, pan=(-0.5 if k % 2 else 0.5))
# heat crackle while glowing
cr = np.zeros(N)
for _ in range(260):
    i = int(rng.uniform(9.5, 18.5)*SR); m = int(0.01*SR); cr[i:i+m] += noise(m)*np.exp(-np.arange(m)/SR*500)*rng.uniform(0.2, 1)
mix += (filt(cr, 1500, 8000)*0.25)[:, None]
# steering actuators
for k in range(9):
    m = int(0.5*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(220+60*(k % 3))*y)*np.hanning(m)*0.5 + filt(noise(m), 400, 1500)*np.hanning(m)*0.4, 13.6+k*0.55, 0.08, pan=(0.4 if k % 2 else -0.4))
# riser into the cut + whoosh
n = int(2.5*SR); x = np.arange(n)/SR
put(filt(noise(n), 400, 7000)*(x/2.5)**2.5, CUT-2.5, 0.2)
n = int(1.2*SR); x = np.arange(n)/SR
put(filt(noise(n), 200, 4000)*np.exp(-x*3), CUT, 0.35)

# --- shot B: ocean ambience, landing burn, legs, touchdown, steam
wb = win(CUT, 29.0, 0.3, 0.6)
for ch in range(2):
    waves = filt(noise(N), 100, 900)*(0.6+0.4*np.sin(2*np.pi*0.15*t + ch*1.3))
    mix[:, ch] += waves*wb*0.06
burn = win(19.8, 26.0, 0.25, 0.25)
roar = filt(noise(N), 30, 900, 3)*1.0 + filt(noise(N), 900, 4000)*0.25
crackle = filt((rng.random(N) > 0.9985).astype(float)*noise(N)*6, 600, 6000)
rumble = np.sin(2*np.pi*34*t)*0.4
eng = (roar + crackle + rumble)*burn*(0.45 + 0.35*np.clip((t-19.8)/5, 0, 1))
mix[:, 0] += eng*0.55; mix[:, 1] += eng*0.55
# ignition boom
n = int(1.5*SR); x = np.arange(n)/SR
put(np.sin(2*np.pi*(48-18*x)*x)*np.exp(-x*2.5) + filt(noise(n), 30, 500)*np.exp(-x*5)*0.7, 19.8, 0.5)
# legs deploying
for k, at in enumerate((23.0, 23.15, 23.3, 23.45)):
    m = int(0.9*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(150+50*y)*y)*np.hanning(m)*0.3 + np.sin(2*np.pi*60*y)*np.exp(-(y-0.75).clip(0)*12)*(y > 0.75)*0.9, at, 0.22, pan=(-0.5 if k % 2 else 0.5))
# touchdown thud + cutoff
n = int(1.8*SR); x = np.arange(n)/SR
put(np.sin(2*np.pi*(55-20*x)*x)*np.exp(-x*3) + filt(noise(n), 40, 400)*np.exp(-x*6)*0.8, 25.6, 0.6)
# steam hiss
n = int(3.2*SR); x = np.arange(n)/SR
put(filt(noise(n), 2000, 9000)*np.exp(-x*0.9)*np.clip(x/0.2, 0, 1), 25.9, 0.12)

# --- quiz bed + ticks
notes = [110, 130.81, 164.81, 146.83]
for k in range(int((DUR-29.0)/0.5)):
    f = notes[(k//2) % 4]; m = int(0.48*SR); y = np.arange(m)/SR
    put((np.sin(2*np.pi*f*y) + 0.4*np.sin(2*np.pi*2*f*y) + 0.15*np.sin(2*np.pi*3*f*y))*np.exp(-y*4), 29.0 + k*0.5, 0.06)
n = int(0.9*SR); x = np.arange(n)/SR
put(filt(noise(n), 300, 5000)*(np.sin(np.pi*x/0.9)**2), 28.2, 0.12)
for at in (31.55, 33.05, 34.75, 36.35):
    m = int(0.12*SR); y = np.arange(m)/SR
    put(np.sin(2*np.pi*(880 + 700*y/0.12)*y)*np.exp(-y*30), at, 0.12)

# --- narration with ducking
voice = np.zeros(N)
for name, at in (("v1", 0.3), ("v2", 8.2), ("v3", 13.5), ("v4", 19.4), ("v5", 23.0), ("v6", 29.1),
                 ("oA", 31.6), ("oB", 33.1), ("oC", 34.8), ("oD", 36.4), ("v7", 38.2)):
    v = load(name); i = int(at*SR); j = min(N, i+len(v)); voice[i:j] += v[:j-i]
duck = 1 - 0.5*np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(4410)/4410, mode="same")
mix *= duck[:, None]
mix += (voice*0.9)[:, None]
mix /= max(1.0, np.max(np.abs(mix))/0.95)
sf.write(QDIR + "/audio/mix.wav", mix, SR)
print("ok")
