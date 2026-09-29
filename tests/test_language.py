import pytest
from PIL import Image

from src.app import service
from src.prompting.language import grounding_phrase
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.prompt_compiler import compile_prompt


@pytest.mark.parametrize('target,expected',[
    ('杯子','cup'),('马克杯','mug'),('手机','cell phone'),
    ('左侧的红色陶瓷杯子','red ceramic cup on the left'),
    ('blue mug','blue mug'),('未知装置','未知装置'),
])
def test_grounding_language_bridge(target,expected):
    assert grounding_phrase(target)==expected


@pytest.mark.parametrize('prompt,target',[
    ('把杯子变成一个陌生物体','杯子'),('将手机替换为虚构物体','手机'),
    ('替换花瓶为新物体','花瓶'),('Replace the blue mug with an unfamiliar object.','blue mug'),
])
def test_bilingual_target_inference(prompt,target):
    assert service.infer_target(prompt)==target


def test_detection_normalizes_worker_input_but_preserves_user_target(monkeypatch,tmp_path):
    payloads=[]
    monkeypatch.setattr(service,'new_run',lambda:tmp_path)
    def run(self,worker,payload):
        payloads.append(payload)
        return {'boxes':[],'labels':[],'scores':[],'masks':[]}
    monkeypatch.setattr(service.ModelManager,'run',run)
    result=service.detect(Image.new('RGB',(32,32)),'杯子')
    assert payloads[0]['target']=='cup'
    assert result['target']=='杯子'
    assert result['grounding_prompt']=='cup'


@pytest.mark.parametrize('text,target',[
    ('把杯子换成带有弯曲琥珀色嵌件的双层结构','杯子'),
    ('Replace the cup with two plates and a curved amber insert.','cup'),
])
def test_design_preserves_bilingual_prompt_and_category_constraints(text,target):
    spec=generate_concepts(text,target,mode='minimal_polish')[0]
    assert spec.raw_user_prompt==text
    assert spec.target_object==target
    assert spec.grounding_prompt=='cup.'
    assert 'cup' in spec.novelty_constraints
    assert text in compile_prompt(spec,'qwen_image')
    # Direct editing preserves the request without injecting template geometry,
    # incompatible materials, or a fictional mask annotation into the prompt.
    assert compile_prompt(spec,'qwen_image')==text
    assert any('drinking rim' in value for value in spec.prohibited_changes)
