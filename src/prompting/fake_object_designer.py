import random
from src.system.paths import config
from src.prompting.schemas import FakeObjectSpec, FictionalObject, Controls
from src.prompting.novelty_rules import exclusions
from src.prompting.scene_constraints import constraints
from src.prompting.negative_prompt import negative_prompt_builder
from src.prompting.prompt_validator import validate_spec
from src.prompting.prompt_compiler import compile_prompt
import yaml
from src.system.paths import ROOT
from src.prompting.language import grounding_phrase

class DeterministicDesigner:
    def generate(self, raw_prompt, target, scene=None, seed=42, mode='autonomous', controls=None, count=3):
        if not target or not target.strip():
            raise ValueError('Specify a target object or use a replacement instruction naming the target.')
        scene = scene or {}; controls = controls or Controls()
        vocab = yaml.safe_load((ROOT/'skills/fake_object_design/templates.yaml').read_text(encoding='utf-8'))
        rng = random.Random(int(seed)); chosen = rng.sample(vocab['templates'], min(count, len(vocab['templates'])))
        result = []
        for i, template in enumerate(chosen):
            physical, preserve, prohibit = constraints(target, scene)
            preserve=list(preserve)+(['Maintain exact non-target texture and fine detail wherever possible'] if controls.preservation>.9 else ['Retain the scene identity and local photographic continuity'])
            material = rng.choice(vocab['material_pairs'])
            if controls.material_complexity < .2: material = material[:1]
            details = [template['secondary'], rng.choice(vocab['details'])]
            if controls.geometry_complexity > .7: details.append(rng.choice(vocab['details']))
            description = 'a category-ambiguous '+template['name'].lower()+' structure'
            primary = template['primary']
            if mode == 'minimal_polish':
                description = raw_prompt
                primary = 'follow the user-specified geometry without adding a new major structure'
                details = ['retain specified geometric details', 'consistent manufactured wall thickness']
            elif mode == 'user_concept':
                description += '; design intent: '+raw_prompt
            colors=rng.sample(vocab['colors'], 2)
            if mode in ['minimal_polish','user_concept']:
                known_materials=list(dict.fromkeys(x for pair in vocab['material_pairs'] for x in pair))+['titanium','steel','glass','wood','copper','aluminum','ceramic','polymer','resin']
                requested=[x for x in known_materials if x in raw_prompt.lower()]
                requested=[x for x in requested if not any(x != y and x in y for y in requested)]
                if requested: material=requested[:3]
                elif mode=='minimal_polish': material=['follow user-specified materials; otherwise a coherent matte manufactured finish']
                requested_colors=[x for x in vocab['colors']+['red','blue','green','amber','black','white'] if x in raw_prompt.lower()]
                if requested_colors: colors=requested_colors[:3]
                elif mode=='minimal_polish': colors=['retain user-specified colors']
            f = FictionalObject(short_identifier=template['id']+' '+template['name'], conceptual_description=description,
                primary_geometry=primary, secondary_structure=details, materials=material,
                colors=colors, surface_properties=['fine photographic microtexture' if controls.realism>.8 else 'restrained experimental surface texture', 'subtle seams and filleted material interfaces'],
                functional_implication='engineered details without an identifiable everyday function' if controls.functional_ambiguity>.5 else 'a subtle recessed tactile interface with unspecified purpose',
                asymmetry='controlled slight asymmetry' if controls.novelty>.6 else 'restrained geometric imbalance', complexity=controls.geometry_complexity)
            spec = FakeObjectSpec(raw_user_prompt=raw_prompt, target_object=target.strip(),
                target_geometry=scene.get('target_geometry', {}), scene={k: scene[k] for k in ['support_surface','nearby_objects','foreground_occlusions','background_context'] if k in scene},
                lighting=scene.get('lighting', {}), camera=scene.get('camera', {}), fictional_object=f,
                novelty_constraints=exclusions(target), physical_constraints=physical, preservation_constraints=preserve,
                prohibited_changes=prohibit, negative_prompt=negative_prompt_builder(scene, any(x in raw_prompt.lower() for x in ['magic','neon','cyberpunk','科幻'])),
                grounding_prompt=grounding_phrase(target).lower().strip().rstrip('.')+'.', seed=int(seed)+i, mode=mode, controls=controls)
            validate_spec(spec)
            if grounding_phrase(target).lower() in ['cup','mug','bottle','vase']:
                spec.prohibited_changes.append('Do not retain a conventional open-top vessel, cup handle, bottle neck, or drinking rim')
            spec.negative_prompt += ', '+', '.join(exclusions(target))
            spec.final_edit_prompt = compile_prompt(spec)
            result.append(spec)
        return result
