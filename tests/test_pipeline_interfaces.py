import json
from PIL import Image
from src.pipelines.brushedit_pipeline import BrushEditPipeline
from src.pipelines.modular_pipeline import ModularPipeline
from src.app import service
from src.system.model_manager import WorkerError

def test_backend_failure_retains_spec_and_masks(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'new_run',lambda:tmp_path)
    image=Image.new('RGB',(64,64),'gray'); m=tmp_path/'candidate.png'
    mask=Image.new('L',(64,64)); from PIL import ImageDraw
    ImageDraw.Draw(mask).rectangle((15,15,45,45),fill=255); mask.save(m)
    det={'image_hash':service.fingerprint(image),'target':'cup','boxes':[[15,15,45,45]],'scores':[.9],'labels':['cup'],'masks':[str(m)]}
    def fail(*args,**kwargs): raise WorkerError('MODEL_UNAVAILABLE: test failure')
    monkeypatch.setattr(service.ModelManager,'run',fail)
    result=service.run_edit(image,'qwen_image','Replace the cup with an unfamiliar object.','cup',0,detection=det)
    assert result.status=='PARTIALLY READY' and result.raw_model_output is None
    assert result.fake_object_spec and result.backend_prompt
    assert (tmp_path/'metadata.json').exists() and (tmp_path/'processed_mask.png').exists()
    assert 'MODEL_UNAVAILABLE' in str(result.warnings)

def test_pipeline_interface_and_prompt_differences():
    a=BrushEditPipeline(); b=ModularPipeline()
    spec=service.generate_concepts('invent','cup')[0]
    assert a.compile_prompt(spec)!=b.compile_prompt(spec)
    a.unload(); b.unload()

def test_stale_detection_fails_before_worker(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'new_run',lambda:tmp_path)
    result=service.run_edit(Image.new('RGB',(50,50)),'brushedit','Replace cup with fictional object.','cup',detection={'image_hash':'old','target':'cup'})
    assert result.status!='READY' and 'changed after detection' in str(result.warnings)
