import numpy as np
from PIL import Image

def strict_composite(original, generated, alpha):
    if generated.size != original.size or alpha.size != original.size:
        raise ValueError('Composite dimensions must match the original.')
    a = np.asarray(alpha.convert('L'), dtype=np.float32)[..., None]/255
    x = np.asarray(original.convert('RGB'), dtype=np.float32)
    y = np.asarray(generated.convert('RGB'), dtype=np.float32)
    return Image.fromarray(np.rint(a*y+(1-a)*x).astype('uint8'))
