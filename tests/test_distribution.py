import importlib.util
import json
from pathlib import Path
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]


def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_release_audit_rejects_runtime_data_and_credentials():
    inspect=script('check_release').inspect_entry
    assert inspect('models/model.safetensors',b'weights')
    assert inspect('.env',b'anything')
    assert inspect('configs/private.txt',('ghp_'+'a'*36).encode())
    assert inspect('docs/too-large.bin',b'x'*(10*1024*1024+1))
    assert not inspect('.env.example',b'# HF_TOKEN is provided via shell')
    assert not inspect('src/app.py',b'print("hello")')


def test_model_bundle_excludes_cache_and_roundtrips_checksum(tmp_path,monkeypatch):
    module=script('package_models')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'MODELS',{'demo':{'path':'models/demo','source':'org/demo','revision':'a'*40}})
    folder=tmp_path/'models/demo';folder.mkdir(parents=True)
    (folder/'weights.bin').write_bytes(b'test weights')
    (folder/'private-cache.txt').write_text('must not ship')
    (tmp_path/'LICENSE_NOTES.md').write_text('Upstream terms apply')
    receipt={'complete':True,'revision':'a'*40,'files':['weights.bin']}
    (folder/'download_receipt.json').write_text(json.dumps(receipt))
    archive=module.package('demo',tmp_path/'bundles')
    module.verify(archive)
    with zipfile.ZipFile(archive) as z:
        assert 'models/demo/weights.bin' in z.namelist()
        assert not any('private-cache' in n for n in z.namelist())
        assert z.read('models/demo/weights.bin')==b'test weights'
    with archive.open('ab') as f:f.write(b'corruption')
    with pytest.raises(ValueError,match='SHA256'):module.verify(archive)


def test_download_rechecks_missing_files_even_with_complete_receipt(tmp_path,monkeypatch):
    import sys
    from types import SimpleNamespace
    module=script('download_models')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'MODELS',{'demo':{'path':'models/demo','source':'org/demo','revision':'b'*40,'patterns':None}})
    folder=tmp_path/'models/demo';folder.mkdir(parents=True)
    (folder/'download_receipt.json').write_text(json.dumps({'complete':True,'revision':'b'*40,'files':['missing.bin']}))
    calls=[]
    def info(source,revision,files_metadata):
        calls.append(revision)
        return SimpleNamespace(sha=revision,siblings=[SimpleNamespace(rfilename='missing.bin',size=4)])
    def download(source,**kwargs):(Path(kwargs['local_dir'])/'missing.bin').write_bytes(b'data')
    monkeypatch.setitem(sys.modules,'huggingface_hub',SimpleNamespace(HfApi=lambda:SimpleNamespace(model_info=info),snapshot_download=download))
    module.download('demo');module.download('demo')
    assert calls==['b'*40]


def test_version_inputs_do_not_embed_local_environments():
    for path in (ROOT/'requirements').rglob('*.txt'):
        text=path.read_text(encoding='utf-8').lower()
        assert 'e:\\fakeobject' not in text and 'file:///' not in text and '-e ' not in text
    repositories=json.loads((ROOT/'configs/repositories.json').read_text())
    assert all(len(r['revision'])==40 for r in repositories.values())
