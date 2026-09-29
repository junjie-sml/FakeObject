import json
from PIL import Image
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

def test_pipeline_delegates_to_qwen(monkeypatch):
    pipeline=ModularPipeline()
    monkeypatch.setattr(service,'run_edit',lambda **kwargs:kwargs)
    assert pipeline.edit(image='example')['pipeline']=='qwen_image'
    assert pipeline.compile_prompt(service.generate_concepts('invent','cup')[0])
    pipeline.unload()

def test_stale_detection_fails_before_worker(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'new_run',lambda:tmp_path)
    result=service.run_edit(Image.new('RGB',(50,50)),'qwen_image','Replace cup with fictional object.','cup',detection={'image_hash':'old','target':'cup'})
    assert result.status!='READY' and 'changed after detection' in str(result.warnings)
