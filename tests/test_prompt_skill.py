import json
import pytest
from src.system.paths import ROOT
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.schemas import FakeObjectSpec, Controls
from src.prompting.prompt_compiler import compile_prompt
from src.prompting.prompt_validator import validate_spec

@pytest.mark.parametrize('target',json.loads((ROOT/'tests/regression/prompt_cases.json').read_text()))
def test_schema_and_scene_invariance(target):
    scene={'support_surface':'oak table','lighting':{'direction':'upper-left','softness':'soft','color_temperature':'warm'}}
    a=generate_concepts('Replace the '+target+' with a fictional object.',target,scene,seed=42)
    b=generate_concepts('Replace the '+target+' with a fictional object.',target,scene,seed=43)
    assert len(a)==3 and len({s.fictional_object.short_identifier for s in a})==3
    assert a[0].scene==b[0].scene and a[0].lighting==b[0].lighting
    assert a[0].target_object==b[0].target_object==target
    assert a[0].fictional_object!=b[0].fictional_object
    assert a[0].model_dump()==generate_concepts('Replace the '+target+' with a fictional object.',target,scene,seed=42)[0].model_dump()
    assert FakeObjectSpec.model_validate_json(a[0].model_dump_json())==a[0]
    assert compile_prompt(a[0],'qwen_image') and a[0].raw_user_prompt

def test_bad_category_detected():
    spec=generate_concepts('invent','cup')[0]
    spec.fictional_object.primary_geometry='a cup with extra handles'
    assert validate_spec(spec).scores.novelty_score<.65

def test_minimal_polish_keeps_user_geometry():
    text='two flat titanium plates joined by a curved amber insert'
    spec=generate_concepts(text,'mug',mode='minimal_polish')[0]
    assert text in compile_prompt(spec)
    assert 'without adding a new major structure' in spec.fictional_object.primary_geometry

def test_controls_validate():
    with pytest.raises(ValueError): Controls(novelty=2)
