import re
from src.prompting.schemas import Scores
from src.prompting.novelty_rules import exclusions

def validate_spec(spec):
    f = spec.fictional_object
    text = ' '.join([f.primary_geometry, f.conceptual_description, *f.secondary_structure]).lower()
    known = [x for x in exclusions(spec.target_object) if re.search(r'\b'+re.escape(x)+r'\b', text)]
    fantasy = any(x in text for x in ['floating', 'magic', 'neon', 'cyberpunk'])
    explicit = any(x in spec.raw_user_prompt.lower() for x in ['magic', 'neon', 'cyberpunk', '科幻', '魔法'])
    scores = Scores(novelty_score=.45 if known else min(.95, .67+.065*len(f.secondary_structure)),
                    plausibility_score=.4 if fantasy and not explicit else .88 if len(f.materials)<=2 else .75,
                    preservation_score=.95 if len(spec.preservation_constraints)>=5 else .5,
                    specificity_score=.9 if f.primary_geometry and f.materials and f.surface_properties else .4)
    warnings = []
    if known: warnings.append('CATEGORY_COLLAPSE_RISK: textual overlap with '+', '.join(known))
    if fantasy and not explicit: warnings.append('PHYSICAL_PLAUSIBILITY_RISK: unrequested fantasy or floating structure')
    spec.scores = scores
    spec.warnings = list(dict.fromkeys(spec.warnings + warnings))
    return spec
