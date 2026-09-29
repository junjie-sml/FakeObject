"""Generate versioned initial data/config assets; never overwrite user configuration."""
from pathlib import Path
import json
import yaml
ROOT = Path(__file__).resolve().parents[1]

def put(path, value):
    dest = ROOT/path; dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding='utf-8')

def main():
    put('configs/app.yaml', {'host':'127.0.0.1','port':7860,'share':False,'max_image_pixels':25000000,'worker_timeout':1800})
    put('configs/paths.yaml', {'models':'models','cache':'data/cache','outputs':'data/outputs','third_party':'third_party'})
    put('configs/hardware_profiles.yaml', {'LOW_VRAM':{'max_side':512,'offload':'sequential','steps':20},'STANDARD':{'max_side':768,'offload':'model','steps':30},'HIGH_VRAM':{'max_side':1024,'offload':'model','steps':40}})
    put('configs/grounded_sam.yaml', {'grounder':'IDEA-Research/grounding-dino-tiny','sam':'facebook/sam2.1-hiera-tiny','sam_config':'configs/sam2.1/sam2.1_hiera_t.yaml','threshold':.3,'text_threshold':.25,'max_candidates':20,'sam_cuda_extension':False})
    put('configs/qwen_image.yaml', {'model_id':'Qwen/Qwen-Image-2.1','pipeline_class':'QwenImage21Pipeline','precision':'bfloat16','offload':'sequential','preview_resolution_tested':False,'mask_strategy':'source_scope','steps':40,'true_cfg_scale':1.0})
    put('configs/preservation_rules.yaml', {'physical':['Respect gravity and a credible center of mass','Maintain support and contact shadows','Retain approximate scale and orientation','Match perspective, light softness, color temperature and shadow direction','Match depth of field and image grain','Respect occlusions and material reflections','Avoid self-intersections and geometry penetration'], 'preserve':['people and faces','hands and clothing','nearby objects','background and architecture','surface textures','text and signage','camera and composition','image dimensions and global color balance'], 'prohibit':['crop','zoom','recompose','restyle','unrelated additions or removals','global illumination changes']})
    put('configs/novelty_rules.yaml', {'default_exclusions':['vase','lamp','speaker','toy','appliance'],'groups':{'mug':['cup','vase','lamp','speaker','toy','kitchen appliance'],'bottle':['vase','thermos','lamp','speaker','container'],'chair':['stool','armchair','bench','toy','appliance']}, 'thresholds':{'novelty':.65,'plausibility':.7,'preservation':.85,'specificity':.7}})
    put('configs/fake_object_skill.yaml', {'preset':'balanced','novelty':.75,'realism':.9,'preservation':.95,'geometry_complexity':.55,'functional_ambiguity':.75,'material_complexity':.35,'max_major_geometry_features':2,'max_materials':3,'anti_scifi_default':True,'anti_category_collapse':True,'prompt_length':'standard','concept_candidates':3,'backend':'DETERMINISTIC_TEMPLATE_FALLBACK', 'presets':{
        'conservative':{'novelty':.55,'realism':.95,'preservation':.98,'geometry_complexity':.35},
        'balanced':{'novelty':.75,'realism':.9,'preservation':.95,'geometry_complexity':.55},
        'highly_novel':{'novelty':.9,'realism':.8,'preservation':.93,'geometry_complexity':.75},
        'experimental':{'novelty':.95,'realism':.65,'preservation':.85,'geometry_complexity':.9}}})
    templates = [
        ('Nested shell','two offset nested shells','an asymmetric opening exposing the inner layer'),
        ('Suspended membrane','a shallow rounded manufactured frame','a thin translucent membrane attached inside a recess'),
        ('Radial hollow fins','an asymmetric solid central body','three short hollow fins of unequal lengths'),
        ('Offset aperture','a flattened softly curved volume','an off-center partial aperture with a material transition'),
        ('Layered collar','three partially overlapping curved layers','an offset inner core anchored to the base'),
        ('Split shell','a compact continuous outer shell','an irregular recessed seam exposing a contrasting layer'),
        ('Partial lattice','a solid rounded volume','one recessed fine lattice region'),
        ('Folded ridge','an asymmetric shallow volume','one continuous ridge of smoothly varying height'),
        ('Hollow channel','a softly faceted connected volume','a narrow channel connecting two recessed openings'),
        ('Bifurcated base','a stable tapered shell','two integrated curved contact zones'),
        ('Inset disc','a flattened rounded prism','a tilted circular inset below the outer surface'),
        ('Soft faceted body','broad smooth facets with nonuniform curvature','a small offset hollow region'),
        ('Translucent core','an opaque protective shell','a partially exposed translucent internal core'),
        ('Discontinuous rim','a low rounded closed body','several separated shallow rim sections'),
        ('Interlocking volumes','two coherent interlocking volumes','a recessed mechanical material interface'),
        ('Recessed interface','a softly tapered asymmetrical volume','a shallow tactile recess without screen or buttons'),
        ('Organic industrial curvature','a synthetic body with smooth biological curvature','a precisely molded folded ridge'),
        ('Offset inner chamber','a thick-walled external shell','a narrow opening into an off-center chamber'),
        ('Segmented surface','one coherent rounded shell','broad irregular regions of subtly differing depth'),
        ('Asymmetric toroid','a partial toroidal body with variable thickness','an offset opening and stable integrated contact face')]
    put('skills/fake_object_design/templates.yaml', {'templates':[{'id':f'T{i+1:02}','name':n,'primary':p,'secondary':s} for i,(n,p,s) in enumerate(templates)],'details':['a shallow recessed channel','a molded transition with consistent wall thickness','a narrow embedded plate','a small frosted inset'], 'material_pairs':[['matte ceramic','frosted polymer'],['fine-grained mineral composite','satin polymer'],['brushed alloy','soft-touch elastomer'],['low-gloss enamel','translucent resin']], 'colors':['off-white','warm gray','blue-gray','desaturated green','pale clay','charcoal','muted amber','ivory','mineral beige']})
    put('configs/benchmark.yaml', {'limit':10,'generate_images':False,'pipeline':'qwen_image','seed':42,'quality':'preview'})
    cases = ['mug on table','bottle on counter','desk lamp','chair','backpack','keyboard','phone','vase','handheld object','partially occluded object','reflective object','transparent object','cluttered small object','multiple same-category objects','low-light object']
    (ROOT/'tests/regression').mkdir(parents=True, exist_ok=True)
    (ROOT/'tests/regression/prompt_cases.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
    (ROOT/'skills/fake_object_design/examples.json').write_text(json.dumps([{'target':x,'prompt':f'Replace the {x} with a semantically unfamiliar manufactured object.'} for x in ['mug','bottle','lamp']], indent=2),encoding='utf-8')
    for directory in (ROOT/'src').rglob('*'):
        if directory.is_dir() and '__pycache__' not in str(directory):
            (directory/'__init__.py').touch(exist_ok=True)

if __name__ == '__main__': main()
