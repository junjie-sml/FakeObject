"""Validate downloaded provenance and image integrity. Does not assign training rights."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.system.paths import ROOT
from PIL import Image

def main():
    records=[json.loads(x) for x in (ROOT/'data/metadata/image_manifest.jsonl').read_text().splitlines()]
    errors=[]
    for r in records:
        p=ROOT/r['local_path']
        try:
            if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']: raise ValueError('Checksum mismatch')
            with Image.open(p) as image: image.verify()
            if not r.get('license') or not r.get('source_page'): raise ValueError('Missing provenance')
        except Exception as e: errors.append({'path':str(p),'error':str(e)})
    report={'total':len(records),'verified':len(records)-len(errors),'errors':errors,'training_eligible':0}
    (ROOT/'data/metadata/dataset_validation.json').write_text(json.dumps(report,indent=2)); print(report)
    if errors: raise SystemExit(1)

if __name__=='__main__': main()
