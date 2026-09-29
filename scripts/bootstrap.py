"""Create isolated environments; heavy image backends are explicitly selected."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from create_envs import create


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--backend',choices=['none','brushedit','qwen','all'],default='none')
    p.add_argument('--full',action='store_true',help='Alias for --backend all')
    p.add_argument('--ui-only',action='store_true',help='CPU UI and tests only, no detection or model downloads')
    p.add_argument('--dataset',action='store_true',help='Optional 50-photo COCO sample; downloads annotation archive too')
    args=p.parse_args()
    backend='all' if args.full else args.backend
    if args.ui_only and backend!='none': p.error('--ui-only cannot be combined with a generation backend')
    if not args.ui_only and not shutil.which('git'): p.error('Install Git and reopen the terminal so git is on PATH.')
    py=create('orchestrator')
    def run(script,*args): subprocess.run([py,str(ROOT/'scripts'/script),*args],check=True,cwd=ROOT)
    if not args.ui_only:
        run('bootstrap_repos.py','--repo','Grounded-SAM-2')
        create('grounded_sam')
        for name in ['grounding_dino','sam2']: run('download_models.py','--model',name)
        if backend in ['brushedit','all']:
            run('bootstrap_repos.py','--repo','BrushEdit')
            create('brushedit'); run('download_models.py','--model','brushedit')
        if backend in ['qwen','all']:
            run('bootstrap_repos.py','--repo','Qwen-Image-2.1')
            create('qwen_image'); run('download_models.py','--model','qwen')
    if args.dataset: run('collect_test_images.py','--count','50')
    if not args.ui_only: run('verify_installation.py')
    run('run_smoke_tests.py',*(['--ui-only'] if args.ui_only else []))
    print('Launch: python scripts/launch_app.py')
    if backend=='none': print('Image generation requires --backend qwen, --backend brushedit or --full.')

if __name__=='__main__': main()
