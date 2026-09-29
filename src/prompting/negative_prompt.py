def negative_prompt_builder(scene=None, allow_scifi=False):
    words = ['cartoon', 'illustration', 'CGI render', 'toy appearance', 'floating geometry', 'duplicate object', 'extra handles', 'distorted background', 'changed camera', 'global restyling', 'halo', 'incorrect shadow', 'wrong scale']
    if not allow_scifi: words += ['magic', 'neon science fiction']
    if any(w in str(scene).lower() for w in ['hand', 'person', 'people', 'face']):
        words += ['changed face', 'extra fingers', 'changed clothing']
    if 'text' in str(scene).lower(): words += ['altered signage', 'random text']
    return ', '.join(words)
