from src.prompting.language import grounding_phrase

def compile_qwen(spec, length='standard'):
    # Direct editing must not inject a fictional template, a different material,
    # or references to an annotation that is not present in the source photo.
    if spec.mode in ['user_concept','minimal_polish']:
        return spec.raw_user_prompt
    target=grounding_phrase(spec.target_object)
    f = spec.fictional_object
    prompt = (f'Replace only the masked {target} with a physically plausible, semantically unfamiliar manufactured object. '
              f'{f.conceptual_description}. Use {f.primary_geometry}, with '+', '.join(f.secondary_structure)+'. '
              'Materials: '+', '.join(f.materials)+', in '+', '.join(f.colors)+'. '+
              'Surfaces: '+', '.join(f.surface_properties)+'. '+f.asymmetry+'. '+f.functional_implication+'. '
              'Avoid clear resemblance to '+', '.join(spec.novelty_constraints)+'. '
              'Keep approximately the original footprint, position, orientation and support. '
              'Match camera perspective, lighting direction and softness, color temperature, material reflections, contact shadows, depth of field and image grain. '
              'Respect gravity, credible weight distribution and existing foreground occlusion. '
              'Preserve people, faces, hands, nearby objects, text, surface textures, background, composition and image dimensions unchanged. '
              'No cropping, global restyling, unrelated additions, impossible intersections or pasted boundaries.')
    if target.lower() in ['cup','mug','bottle','vase']:
        prompt += ' Replace the recognizable vessel silhouette and drinking rim with a closed asymmetrical body; any opening is a small side recess.'
    if length == 'detailed':
        prompt += ' ' + '; '.join(spec.physical_constraints)+'. Scene: '+spec.scene.model_dump_json()+'. Lighting: '+spec.lighting.model_dump_json()+'.'
    elif length == 'compact':
        prompt = (f'Replace only {target}: {f.conceptual_description}; {f.primary_geometry}; '+', '.join(f.secondary_structure)+
                  '; '+', '.join(f.materials)+'; '+', '.join(f.colors)+'. Avoid '+', '.join(spec.novelty_constraints)+
                  '. Match original scale, support, gravity, perspective, shadows, reflections, lighting and focus. Preserve all non-target pixels, people and occlusions unchanged.')
    # User intent must survive every mode and length, including autonomous and
    # compact. Generated templates are fallback ideas, never replacements for it.
    return ('USER REQUEST: '+spec.raw_user_prompt+'\n'
            'The user-specified material, shape and style take priority. Use the following design ideas only for unspecified details; '
            'ignore any suggested material, geometry or category exclusion that conflicts with the request.\n'+prompt)
