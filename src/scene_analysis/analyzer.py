"""Conservative geometry analysis; no invented semantic or illumination observations."""
import numpy as np

def analyze_scene(image, mask=None, target='object'):
    geometry = {'approximate_shape': 'match target bounding volume', 'apparent_size': 'same as original', 'orientation': 'match original', 'bounding_box_ratio': None}
    if mask is not None:
        yy, xx = np.where(np.asarray(mask.convert('L')) > 127)
        if len(xx):
            geometry['bounding_box_ratio'] = round((xx.max()-xx.min()+1)/(yy.max()-yy.min()+1), 3)
    return {'target': target, 'target_geometry': geometry,
            'support_surface': 'retain the existing support and contact points', 'nearby_objects': [],
            'foreground_occlusions': [], 'background_context': 'preserve original photograph',
            'lighting': {'direction': 'match source', 'softness': 'match source', 'color_temperature': 'match source'},
            'camera': {'viewpoint': 'match source', 'depth_of_field': 'match source'},
            'method': 'geometry + conservative fallback',
            'warnings': ['No semantic VLM loaded; lighting and support are preservation constraints, not measured estimates. Supply an occluder mask for exact foreground protection.']}
