from src.system.paths import config

def constraints(target, scene):
    rules = config('preservation_rules')
    physical = list(rules['physical'])
    t = target.lower() + ' ' + str(scene).lower()
    if any(x in t for x in ['handheld', 'phone', 'hand', '手']):
        physical.append('Maintain hand-object contact and finger occlusion; keep anatomy unchanged')
    if any(x in t for x in ['chair', 'furniture', '椅']):
        physical.append('Keep the original floor contact and bounding volume; preserve nearby people')
    if any(x in t for x in ['transparent', 'glass', '透明']):
        physical.append('Reconstruct the background seen through the old transparent object')
    if 'wall' in t:
        physical.append('Preserve wall attachment, depth from wall, and localized shadow')
    return physical, rules['preserve'], rules['prohibit']
