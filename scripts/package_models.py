"""Optional ZIP64 model-only bundles for a collaborator's authorized offline transfer.

No upload is performed. Only files listed in the model's download receipt are
included, plus that receipt and the project's upstream-license guidance.
"""
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.models.model_registry import MODELS


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()


def package(name,output):
    entry=MODELS[name]; folder=ROOT/entry['path']; receipt=folder/'download_receipt.json'
    saved=json.loads(receipt.read_text(encoding='utf-8'))
    if not saved.get('complete') or saved.get('revision')!=entry['revision'] or not saved.get('files'):
        raise ValueError('Complete pinned model download required before packaging.')
    paths=[]
    for relative in [*saved['files'],'download_receipt.json']:
        path=(folder/relative).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            raise ValueError('Missing or invalid receipt path: '+relative)
        paths.append(path)
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    final=output/f'{name}-{entry["revision"][:12]}.zip'
    if final.exists(): raise FileExistsError(f'{final} already exists; verify or choose a new output folder.')
    if shutil.disk_usage(output).free < sum(p.stat().st_size for p in paths)+1024**3:
        raise RuntimeError('Insufficient space for an uncompressed ZIP64 bundle plus 1 GiB margin.')
    part=final.with_suffix('.zip.part')
    with zipfile.ZipFile(part,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
        for path in paths:
            print('Packing',path.relative_to(ROOT),flush=True)
            z.write(path,path.relative_to(ROOT).as_posix())
        z.write(ROOT/'LICENSE_NOTES.md','MODEL_LICENSE_NOTES.md')
        z.writestr('MODEL_BUNDLE.json',json.dumps({'model':name,'source':entry['source'],'revision':entry['revision']},indent=2))
    part.replace(final)
    digest=sha256(final)
    final.with_suffix('.zip.sha256').write_text(digest+'  '+final.name+'\n',encoding='utf-8')
    print('Bundle:',final,'SHA256:',digest)
    return final


def verify(path):
    path=Path(path)
    expected=path.with_suffix('.zip.sha256').read_text(encoding='utf-8').split()[0]
    if sha256(path)!=expected: raise ValueError('SHA256 mismatch; do not extract this bundle.')
    print('SHA256 OK:',path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    choice=p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--model',choices=list(MODELS)); choice.add_argument('--verify',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'dist/model-bundles')
    args=p.parse_args()
    if args.verify: verify(args.verify)
    else: package(args.model,args.output)

if __name__=='__main__': main()
