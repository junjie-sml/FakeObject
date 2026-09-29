import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def create(name):
    if sys.version_info[:2] != (3,11):
        raise SystemExit('Use Python 3.11 to build these tested environments (python --version).')
    folder=ROOT/'envs'/name
    py=folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not py.exists(): venv.EnvBuilder(with_pip=True).create(folder)
    env=os.environ.copy(); env['PIP_CACHE_DIR']=str(ROOT/'data/cache/pip'); env.setdefault('SAM2_BUILD_CUDA','0')
    def pip(*args): subprocess.run([str(py),'-m','pip',*args],check=True,cwd=ROOT,env=env)
    pip('install','wheel','setuptools>=68,<81')
    constraints=str(ROOT/'requirements/constraints'/f'{name}.txt')
    if name=='orchestrator': pip('install','-c',constraints,'-e','.','pytest')
    else:
        old=name=='brushedit'
        pip('install','torch==2.0.1' if old else 'torch==2.6.0','torchvision==0.15.2' if old else 'torchvision==0.21.0','--index-url','https://download.pytorch.org/whl/'+('cu118' if old else 'cu124'))
        pip('install','-c',constraints,'-r',str(ROOT/'requirements'/f'{name}.txt'))
        if name in ['brushedit','grounded_sam']:
            pip('install','-c',constraints,'--no-build-isolation','-e','third_party/'+('BrushEdit' if old else 'Grounded-SAM-2'))
    pip('check')
    frozen=subprocess.check_output([str(py),'-m','pip','freeze'],text=True)
    (folder/'requirements.lock.txt').write_text(frozen,encoding='utf-8')
    return str(py)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=['all','orchestrator','grounded_sam','brushedit','qwen_image'],default='orchestrator'); args=p.parse_args()
    for worker in ['orchestrator','grounded_sam','brushedit','qwen_image'] if args.worker=='all' else [args.worker]:
        try: print(create(worker))
        except subprocess.CalledProcessError as e:
            raise SystemExit(f'Environment {worker} failed at command {e.cmd}. Full output above. Retry: python scripts/create_envs.py --worker {worker}')
