import argparse
import csv
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.system.paths import ROOT
from src.app.service import detect,run_edit
from src.prompting.fake_object_skill import generate_concepts

def main():
    p=argparse.ArgumentParser(); p.add_argument('--limit',type=int,default=10); p.add_argument('--generate',choices=['qwen_image']); args=p.parse_args()
    rows=[json.loads(x) for x in (ROOT/'data/metadata/image_manifest.jsonl').read_text().splitlines()][:args.limit]
    results=[]
    targets=['cup','bottle','chair','backpack','cell phone','keyboard','vase','book','bowl','laptop','wine glass','remote','handbag','clock']
    for row in rows:
        start=time.perf_counter(); target=row.get('primary_target') or next((x for x in targets if x in row['candidate_objects']),row['candidate_objects'][0]); out={'image':row['local_path'],'target':target,'detection_success':False,'runtime':0,'peak_gpu_mb':None,'outside_mae':None,'category_collapse_score':None,'human_rating':None,'output_path':None,'error':None}
        try:
            det=detect(ROOT/row['local_path'],target); out['detection_success']=bool(det['masks']); out['peak_gpu_mb']=det.get('peak_gpu_memory_mb')
            if not det['masks']: out['error']='NO_DETECTIONS: '+ '; '.join(det.get('warnings',[]))
            spec=generate_concepts('Replace the '+target+' with an unfamiliar manufactured object.',target)[0]
            if args.generate:
                if len(det['masks'])!=1: raise ValueError('Ambiguous candidates: select an instance in the UI; benchmark does not choose arbitrarily.')
                r=run_edit(ROOT/row['local_path'],args.generate,spec.raw_user_prompt,target,0,detection=det,spec=spec)
                out['output_path']=r.output_dir; out['outside_mae']=r.evaluation.get('strict',{}).get('outside_mae'); out['peak_gpu_mb']=r.hardware_stats.get('peak_gpu_memory_mb'); out['error']='; '.join(r.warnings) if r.status!='READY' else None
        except Exception as e: out['error']=str(e)
        out['runtime']=round(time.perf_counter()-start,3); results.append(out); print(out,flush=True)
    dest=ROOT/'data/benchmarks'
    (dest/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results),encoding='utf-8')
    if results:
        with (dest/'results.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)

if __name__=='__main__': main()
