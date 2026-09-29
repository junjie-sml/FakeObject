"""Evaluate saved outputs without regenerating images."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.system.paths import ROOT
from src.system.model_manager import ModelManager

def main():
    p=argparse.ArgumentParser(); p.add_argument('--metadata',type=Path); args=p.parse_args()
    paths=[args.metadata] if args.metadata else list((ROOT/'data/outputs').glob('*/*/metadata.json'))
    for path in paths:
        r=json.loads(path.read_text(encoding='utf-8'))
        if not r.get('strict_output'): continue
        response=ModelManager().run('grounded_sam',{'action':'evaluate','image':r['original_image'],'output':r['strict_output'],'mask':r['processed_mask'],'target':r['target_object']})
        r['evaluation']['category_diagnostics']=response['category_diagnostics']
        r['runtime']['category_evaluation']=response['runtime']
        path.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
        print(r['run_id'],json.dumps(response['category_diagnostics']),flush=True)

if __name__=='__main__': main()
