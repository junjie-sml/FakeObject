import hashlib
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
from src.app import service
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.prompt_compiler import compile_prompt
from src.prompting.selected_region import describe_selected_region,bind_qwen_prompt
from src.postprocessing.qwen_conditioning import mask_references
from src.workers.qwen_worker import QwenImageEditor
from src.workers.common import resize_for_inference


def detections(tmp_path):
    masks=[]
    for i,box in enumerate([(0,10,100,90),(30,10,70,40)]):
        image=Image.new('L',(100,100)); image.paste(255,box)
        p=tmp_path/f'mask{i}.png'; image.save(p); masks.append(str(p))
    return {'masks':masks,'boxes':[[0,10,100,90],[30,10,70,40]],
            'labels':['building','tower'],'scores':[.8,.7]}


def test_whole_building_and_tower_have_distinct_scope(tmp_path):
    det=detections(tmp_path)
    whole=describe_selected_region(det,0,Image.open(det['masks'][0]))
    part=describe_selected_region(det,1,Image.open(det['masks'][1]))
    assert whole['display_number']==1 and part['display_number']==2
    assert whole['contained_candidates']==[{'index':1,'label':'tower'}]
    assert part['contained_candidates']==[]
    assert whole['mask_pixels']==8000 and part['mask_pixels']==1200
    assert '不能只改上部塔楼' in bind_qwen_prompt('design','水晶建筑',whole)
    assert '整个塔楼' in bind_qwen_prompt('design','水晶建筑',part)
    assert '两侧墙面' not in bind_qwen_prompt('design','水晶建筑',part)
    assert 'entire building' in bind_qwen_prompt('design','Crystal building',whole)


def test_reference_tags_match_original_and_selected_mask_order(tmp_path):
    det=detections(tmp_path)
    source=Image.new('RGB',(100,100),(30,90,210))
    mask=Image.open(det['masks'][0])
    references,prompt=mask_references(source,mask,'水晶建筑')
    assert np.array_equal(np.array(references[0]),np.array(source))
    assert np.array_equal(np.array(references[1].convert('L')),np.array(mask))
    assert '<image1>' in prompt and '<image2>' in prompt and '<image3>' not in prompt
    assert '水晶建筑' in prompt
    with pytest.raises(ValueError): mask_references(source,Image.new('L',(5,5),255),'edit')
    with pytest.raises(ValueError): mask_references(source,Image.new('L',(100,100)),'edit')


def test_default_qwen_conditioning_keeps_source_colors_and_does_not_render_mask(tmp_path,monkeypatch):
    source=Image.new('RGB',(270,196),(100,130,170))
    source.paste((20,30,40),(40,60,120,130))
    original=tmp_path/'original.png'; mask=tmp_path/'mask.png'; output=tmp_path/'output.png'
    source.save(original); Image.new('L',source.size,255).save(mask)
    calls=[]
    def pipe(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(images=[kwargs['image']])
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(Generator=lambda device:SimpleNamespace(manual_seed=lambda seed:seed)))
    editor=QwenImageEditor(); editor.pipe=pipe
    monkeypatch.setattr(editor,'load',lambda *args:None)
    monkeypatch.setattr(editor,'unload',lambda:None)
    result=editor.edit({'image':str(original),'mask':str(mask),'output':str(output),'prompt':'水晶建筑'})
    assert result['mask_strategy']=='source_scope'
    assert isinstance(calls[0]['image'],Image.Image)
    assert np.array_equal(np.array(calls[0]['image']),np.array(resize_for_inference(source,512,32,allow_upscale=True)))
    assert calls[0]['num_inference_steps']==40
    assert '水晶建筑' in calls[0]['prompt']


@pytest.mark.parametrize('mode',['autonomous','exploration','user_concept','minimal_polish'])
@pytest.mark.parametrize('length',['compact','standard','detailed'])
def test_original_request_survives_every_qwen_mode_and_length(mode,length):
    raw='将建筑换成一个风格类似但是是水晶做的假建筑'
    spec=generate_concepts(raw,'建筑',mode=mode)[0]
    assert raw in compile_prompt(spec,'qwen_image',length)


@pytest.mark.parametrize('index',[0,1])
def test_worker_receives_selected_mask_and_auditable_scope(tmp_path,monkeypatch,index):
    det=detections(tmp_path); original=Image.new('RGB',(100,100),'gray')
    det.update(image_hash=service.fingerprint(original),target='建筑')
    output=tmp_path/'run'; output.mkdir()
    monkeypatch.setattr(service,'new_run',lambda:output)
    requests=[]
    def run(self,worker,payload,**kwargs):
        if payload['action']=='evaluate': return {'category_diagnostics':{},'runtime':0}
        requests.append(payload)
        Image.new('RGB',(100,100),'blue').save(payload['output'])
        return {'output':payload['output'],'runtime':0,'model_ids':['test']}
    monkeypatch.setattr(service.ModelManager,'run',run)
    raw='将建筑换成水晶建筑'
    result=service.run_edit(original,'qwen_image',raw,'建筑',index,detection=det,backend_prompt='Custom geometry details',prompt_mode='user_concept')
    assert result.status=='READY'
    assert raw in requests[0]['prompt'] and 'Custom geometry details' in requests[0]['prompt']
    expected=Image.open(det['masks'][index]).convert('L')
    assert np.array_equal(np.array(expected),np.array(Image.open(result.raw_mask)))
    assert result.selected_region['mask_sha256']==hashlib.sha256(expected.tobytes()).hexdigest()
    assert result.selected_region['index']==index
    assert result.fake_object_spec['mode']=='user_concept'
    assert requests[0]['steps']==40
    assert ('整个建筑物' if index==0 else '整个塔楼') in requests[0]['prompt']
