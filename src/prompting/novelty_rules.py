from src.system.paths import config
from src.prompting.language import grounding_phrase

def exclusions(target):
    target=grounding_phrase(target)
    rules = config('novelty_rules')
    words = rules['groups'].get(target.lower(), rules['default_exclusions'])
    return list(dict.fromkeys([target] + words))[:8]
