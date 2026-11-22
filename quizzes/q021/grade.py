import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# vignette
_v = ((xx - W/2)/(W*0.75))**2 + ((yy - H/2)/(H*0.7))**2
VIG = np.clip(1 - 0.35*_v, 0.55, 1)[..., None]
# warm haze band around the horizon (~y 1340)
def haze_mask(hy):
    d = (yy - hy)/260.0
    return (np.exp(-d*d)*0.55)[..., None]
HAZE_COL = np.array([255, 196, 150], np.float32)
_rng = np.random.default_rng(0)
GRAIN = [(_rng.standard_normal((H, W, 1)).astype(np.float32)*5.0) for _ in range(6)]

def grade(img, i=0, horizon_y=1478):
    if img.size != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    a = np.asarray(img.convert("RGB"), np.float32)
    # bloom
    bright = np.clip(a - 200, 0, None)
    if bright.max() > 0:
        bl = np.asarray(Image.fromarray(bright.astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)), np.float32)
        a = a + bl*0.6
    m = haze_mask(horizon_y)
    a = a*(1-m) + HAZE_COL*m
    # teal/orange split: cool shadows, warm highlights
    lum = a.mean(axis=2, keepdims=True)/255.0
    a = a + (np.array([-6, 2, 10], np.float32)*(1-lum)) + (np.array([10, 4, -8], np.float32)*lum)
    # contrast S-curve
    x = np.clip(a/255.0, 0, 1)
    x = x*x*(3-2*x)*0.35 + x*0.65
    a = x*255.0
    a = a*VIG + GRAIN[i % len(GRAIN)]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

if __name__ == "__main__":
    import sys
    grade(Image.open(sys.argv[1])).save(sys.argv[2])
