"""Run one real photo through detection and a selected image backend."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.system.paths import ROOT
from src.app.service import detect, run_edit

def main():
    p=argparse.ArgumentParser(); p.add_argument('--pipeline',choices=['qwen_image'],default='qwen_image'); p.add_argument('--steps',type=int,default=None); args=p.parse_args()
    rows=[json.loads(x) for x in (ROOT/'data/metadata/image_manifest.jsonl').read_text().splitlines()]
    row=rows[0]; path=ROOT/row['local_path']
    cached=ROOT/'data/metadata/demo_detection.json'
    if cached.exists():
        detection=json.loads(cached.read_text())
        from src.app.service import fingerprint,load_image
        if detection['image_hash']!=fingerprint(load_image(path)): detection=detect(path,'cup')
    else: detection=detect(path,'cup')
    cached.write_text(json.dumps(detection,indent=2),encoding='utf-8')
    # This scripted smoke test explicitly selects the largest candidate. Interactive UI never does.
    idx=max(range(len(detection['boxes'])),key=lambda i:(detection['boxes'][i][2]-detection['boxes'][i][0])*(detection['boxes'][i][3]-detection['boxes'][i][1]))
    result=run_edit(path,args.pipeline,'Replace the cup with an unfamiliar manufactured object that does not correspond to a known everyday product.','cup',idx,detection=detection,steps=args.steps,mask_settings={'mask_dilation_ratio':.02,'mask_feather_px':3})
    print(result.model_dump_json(indent=2))
    report=ROOT/f'data/metadata/demo_{args.pipeline}.json'; report.write_text(result.model_dump_json(indent=2),encoding='utf-8')
    if result.status!='READY': raise SystemExit(1)

if __name__=='__main__': main()
