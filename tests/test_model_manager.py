import json
import subprocess
import pytest
from pathlib import Path
from src.system import model_manager as mm

def test_worker_crash_releases_lock_and_records_log(tmp_path,monkeypatch):
    (tmp_path/'data/cache/ipc').mkdir(parents=True); (tmp_path/'logs/workers').mkdir(parents=True)
    monkeypatch.setattr(mm,'ROOT',tmp_path)
    monkeypatch.setattr(mm,'python_for',lambda _:Path(__file__))
    monkeypatch.setattr(mm.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,7))
    manager=mm.ModelManager()
    with pytest.raises(mm.WorkerError,match='exited'): manager.run('grounded_sam',{})
    assert manager.state=='NONE' and not manager.lock.is_locked

def test_gpu_lock_excludes_second_owner(tmp_path):
    from filelock import FileLock,Timeout
    one=FileLock(str(tmp_path/'gpu.lock')); two=FileLock(str(tmp_path/'gpu.lock'))
    with one:
        with pytest.raises(Timeout): two.acquire(timeout=0)
    with two.acquire(timeout=0): pass
