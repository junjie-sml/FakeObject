import numpy as np
from scipy import ndimage as ndi

FAILURE_TYPES = ['WRONG_TARGET','INCOMPLETE_MASK','SOURCE_OBJECT_REMAINS','CATEGORY_COLLAPSE','GLOBAL_RESTYLE','BACKGROUND_CHANGED','FLOATING_OBJECT','BAD_CONTACT','SHADOW_MISMATCH','PERSPECTIVE_MISMATCH','MALFORMED_GEOMETRY','MASK_LEAKAGE','CGI_APPEARANCE','CUDA_OOM','MODEL_UNAVAILABLE']

def evaluate(original, output, mask, boundary_px=5):
    a = np.asarray(original.convert('RGB'), dtype=float)
    b = np.asarray(output.convert('RGB'), dtype=float)
    m = np.asarray(mask.convert('L')) > 0
    outside = ~ndi.binary_dilation(m, iterations=max(1, boundary_px))
    delta = np.abs(a-b)
    mse = float(np.mean((a[outside]-b[outside])**2)) if outside.any() else None
    band = ndi.binary_dilation(m, iterations=boundary_px) ^ ndi.binary_erosion(m, iterations=boundary_px)
    result = {'outside_mae': float(delta[outside].mean()) if outside.any() else None,
              'outside_max_change': float(delta[outside].max()) if outside.any() else None,
              'outside_psnr_db': None if mse is None or mse == 0 else float(10*np.log10(255**2/mse)),
              'outside_exact': bool(np.array_equal(a[outside], b[outside])) if outside.any() else None,
              'boundary_mae': float(delta[band].mean()) if band.any() else None,
              'category_collapse': {'status': 'SEPARATE_DIAGNOSTIC', 'reason': 'This block measures pixels only. See top-level category_diagnostics for optional CLIP measurements on the strict result.'},
              'source_object_leakage': None, 'realism': None, 'human_ratings': None,
              'note': 'Pixel diagnostics are not perceptual quality or novelty proof; infinite PSNR encoded as null when exact.'}
    result['warnings'] = ['BACKGROUND_CHANGED'] if result['outside_mae'] and result['outside_mae'] > 3 else []
    return result
