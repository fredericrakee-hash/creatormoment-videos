import numpy as np
from PIL import Image
_g = None
def look(img):
    global _g
    a = np.asarray(img, np.float32)/255.0
    if _g is None or _g.shape[0] != a.shape[0]:
        y = np.linspace(0, 1, a.shape[0], dtype=np.float32)[:, None, None]
        _g = 0.78 + 0.22*np.clip(y/0.55, 0, 1)    # deeper sky towards the top of the frame
    a = a**1.2
    a = a*np.array([1.03, 0.96, 0.86], np.float32)
    a = a*np.concatenate([_g*1.0, _g*0.99, _g*1.04], axis=2)
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum)*1.1
    return Image.fromarray(np.clip(a*255, 0, 255).astype(np.uint8))
