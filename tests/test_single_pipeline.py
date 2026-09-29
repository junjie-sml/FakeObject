import json
import re
import pytest
from scripts import bootstrap
from scripts.create_envs import WORKERS, create
from src.system.paths import ROOT, config
from src.system.model_manager import ModelManager, WorkerError
from src.prompting.prompt_compiler import compile_prompt
from src.prompting.fake_object_skill import generate_concepts

@pytest.mark.parametrize('args,workers,models',[
    ([], WORKERS, ['grounding_dino','sam2','qwen']),
    (['--ui-only'], ['orchestrator'], []),
    (['--backend','none'], ['orchestrator','grounded_sam'], ['grounding_dino','sam2']),
    (['--backend','qwen'], WORKERS, ['grounding_dino','sam2','qwen']),
    (['--full'], WORKERS, ['grounding_dino','sam2','qwen']),
])
def test_installation_profiles(monkeypatch,args,workers,models):
    created=[]; commands=[]
    monkeypatch.setattr(bootstrap,'create',lambda name:created.append(name) or 'python')
    monkeypatch.setattr(bootstrap.shutil,'which',lambda name:'git')
    monkeypatch.setattr(bootstrap.subprocess,'run',lambda command,**kwargs:commands.append(command))
    bootstrap.main(args)
    assert created==workers
    assert [c[-1] for c in commands if '--model' in c]==models


def test_reject_unknown_backends_before_loading():
    with pytest.raises(ValueError): create('retired_backend')
    with pytest.raises(WorkerError): ModelManager().run('retired_backend',{})
    with pytest.raises(ValueError): compile_prompt(generate_concepts('invent','cup')[0],'retired_backend')
    assert {v['pipeline'] for v in config('models').values()}=={'grounded_sam','qwen_image','evaluation'}


def test_ui_has_one_generation_pipeline():
    from src.ui.app import make_app
    app=make_app()
    try:
        cfg=app.get_config_file()
        components=cfg['components']
        assert len([c for c in components if c['type']=='tabitem'])==6
        assert any(type(c).__name__=='State' and c.value=='qwen_image' for c in app.blocks.values())
        assert 'brushedit' not in json.dumps(cfg,default=str).lower()
        assert 'brushnet' not in json.dumps(cfg,default=str).lower()
    finally: app.close()


def test_readme_is_english():
    text=(ROOT/'README.md').read_text(encoding='utf-8')
    assert not re.search(r'[\u3400-\u9fff]',text)
    assert 'brushedit' not in text.lower()
