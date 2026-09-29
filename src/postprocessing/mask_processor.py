import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

def process_mask(mask, mask_dilation_px=None, mask_dilation_ratio=.02, mask_feather_px=3,
                 cleanup_min_component=32, erosion_px=0, preserve_occluders=None, fill_holes=True):
    values = np.asarray(mask.convert('L') if isinstance(mask, Image.Image) else mask)
    raw = values > (.5 if values.size and values.max()<=1 else 127)
    if raw.ndim != 2 or not raw.any():
        raise ValueError('EMPTY_MASK: choose another detection or provide a non-empty mask.')
    labels, _ = ndi.label(raw)
    counts = np.bincount(labels.ravel())
    keep = counts >= int(cleanup_min_component)
    keep[0] = False
    clean = keep[labels]
    if not clean.any():
        raise ValueError('Cleanup removed the complete mask. Lower cleanup_min_component.')
    # Whole-object replacement usually includes contents of cups/transparent objects.
    # Disable full filling for real apertures; occluders are protected after morphology.
    holes = ndi.binary_fill_holes(clean) & ~clean
    hl, _ = ndi.label(holes)
    hc = np.bincount(hl.ravel())
    small = hc <= max(16, int(cleanup_min_component)); small[0] = False
    clean |= small[hl]
    if fill_holes: clean = ndi.binary_fill_holes(clean)
    yy, xx = np.where(clean)
    radius = int(np.clip(round((xx.max()-xx.min()+1)*mask_dilation_ratio), 1, 32)) if mask_dilation_px is None or mask_dilation_px<0 else int(mask_dilation_px)
    if erosion_px > 0:
        clean = ndi.binary_erosion(clean, iterations=int(erosion_px))
    if radius > 0:
        clean = ndi.distance_transform_edt(~clean) <= radius
    if not clean.any():
        raise ValueError('Erosion removed the whole mask.')
    # Feather inward, so the hard edit support has mathematically exact zero outside.
    alpha = np.clip(ndi.distance_transform_edt(clean) / max(1, float(mask_feather_px)), 0, 1) if mask_feather_px else clean.astype(float)
    if preserve_occluders is not None:
        ov = np.asarray(preserve_occluders.convert('L') if isinstance(preserve_occluders, Image.Image) else preserve_occluders)
        occ = ov > (.5 if ov.size and ov.max()<=1 else 127)
        if occ.shape != clean.shape:
            raise ValueError('Occluder mask must match original image dimensions.')
        alpha[occ] = 0
        clean[occ] = False
    return Image.fromarray((clean*255).astype('uint8')), Image.fromarray(np.rint(alpha*255).astype('uint8'))

def mask_overlay(image, mask):
    rgb = np.asarray(image.convert('RGB')).astype(float)
    a = (np.asarray(mask.convert('L'))/255*.42)[..., None]
    return Image.fromarray(np.uint8(rgb*(1-a)+np.array([24, 220, 174])*a))

def bbox_overlay(image, boxes, labels=None, scores=None):
    out = image.convert('RGB').copy(); draw = ImageDraw.Draw(out)
    for i, box in enumerate(boxes):
        draw.rectangle(box, outline='#12be9b', width=3)
        text = f'{i+1}: {labels[i] if labels else "target"}'
        if scores: text += f' {scores[i]:.2f}'
        draw.text((box[0]+3, box[1]+3), text, fill='white', stroke_width=2, stroke_fill='black')
    return out
