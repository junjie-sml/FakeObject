import argparse
import json
import shutil
import sys
from pathlib import Path
from fnmatch import fnmatch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.models.model_registry import MODELS
from src.system.paths import ROOT

def download(name):
    from huggingface_hub import HfApi, snapshot_download
    entry = MODELS[name]; dest = ROOT/entry['path']; dest.mkdir(parents=True,exist_ok=True)
    receipt = dest/'download_receipt.json'
    saved=json.loads(receipt.read_text()) if receipt.exists() else {}
    revision=entry['revision']
    if (saved.get('complete') and saved.get('revision')==revision and saved.get('files')
            and all((dest/f).is_file() for f in saved['files'])):
        print(f'{name}: already downloaded at {revision}'); return
    info = HfApi().model_info(entry['source'],revision=revision,files_metadata=True)
    files = [f for f in info.siblings if not entry['patterns'] or any(fnmatch(f.rfilename,p) for p in entry['patterns'])]
    size = sum(f.size or 0 for f in files)
    print(f'{name}: {size/2**30:.2f} GiB, revision {info.sha}',flush=True)
    if shutil.disk_usage(ROOT).free < size + 3*2**30:
        raise RuntimeError(f'Insufficient disk space for {name}: requires {size/2**30:.1f} GiB + 3 GiB margin.')
    snapshot_download(entry['source'],revision=info.sha,local_dir=dest,allow_patterns=entry['patterns'],max_workers=4)
    receipt.write_text(json.dumps({'complete':True,'revision':info.sha,'source':entry['source'],'required_disk_bytes':size,'files':[f.rfilename for f in files]},indent=2),encoding='utf-8')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--model',choices=[*MODELS,'all'],default='grounding_dino'); args=parser.parse_args()
    for name in MODELS if args.model=='all' else [args.model]: download(name)
