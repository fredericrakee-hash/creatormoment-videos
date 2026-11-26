import numpy as np
from PIL import Image
def warm(img):
    a = np.asarray(img, np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = np.clip((r - b - 25)/60, 0, 1)*np.clip((r - 150)/60, 0, 1)
    a[..., 1] = g - m*(g - r*0.62)*0.8
    a[..., 2] = b - m*(b - r*0.22)*0.85
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
