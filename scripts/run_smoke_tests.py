import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.system.paths import config,python_for
from src.system.hardware import detect_hardware
from src.system.model_manager import ModelManager
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.prompt_compiler import compile_prompt
from src.postprocessing.mask_processor import process_mask
from src.app.service import detect,select_mask,load_image
import numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('--inference',action='store_true'); p.add_argument('--ui-only',action='store_true'); args=p.parse_args()
    results={}
    def check(name,fn):
        try: results[name]={'status':'PASS','details':fn()}
        except Exception as e: results[name]={'status':'FAIL','error':str(e)}
    check('hardware',detect_hardware)
    check('config',lambda:config('app'))
    manifest=ROOT/'data/metadata/image_manifest.jsonl'
    rows=[json.loads(x) for x in manifest.read_text().splitlines()] if manifest.exists() else []
    from PIL import Image
    check('image_load',lambda:list(load_image(ROOT/rows[0]['local_path'] if rows else Image.new('RGB',(64,64))).size))
    def prompt():
        specs=generate_concepts('Replace the cup with an unfamiliar manufactured object.','cup')
        assert len(specs)==3 and compile_prompt(specs[0]); return specs[0].scores.model_dump()
    check('spec_and_prompt',prompt)
    def mask():
        m=np.zeros((80,80),dtype='uint8'); m[20:50,20:50]=255
        h,a=process_mask(m); assert np.asarray(h).sum()>0; return {'nonempty':True}
    check('mask_processing',mask)
    for worker in ['grounded_sam','qwen_image']:
        if args.ui_only or not python_for(worker).exists():
            results[worker+'_health']={'status':'SKIPPED','reason':'UI-only check or optional environment not installed'}
            continue
        def worker_health(w=worker):
            r=ModelManager().run(w,{'action':'health'},timeout=120)
            if r.get('errors'): raise RuntimeError('; '.join(r['errors']))
            return r
        check(worker+'_health',worker_health)
    if args.inference:
        def grounding():
            if not rows: raise ValueError('Download demo photos first: python scripts/collect_test_images.py --count 50')
            r=detect(ROOT/rows[0]['local_path'],'cup'); assert len(r['masks'])>0
            assert np.asarray(select_mask(r,0)).sum()>0
            return r
        check('actual_grounding_segmentation',grounding)
    else: results['actual_grounding_segmentation']={'status':'SKIPPED','reason':'Use --inference'}
    for backend in ['qwen_image']:
        p=ROOT/f'data/metadata/demo_{backend}.json'
        if p.exists():
            r=json.loads(p.read_text()); results[backend+'_actual_edit']={'status':'PASS' if r['status']=='READY' else 'FAIL','result':r['output_dir'],'warnings':r['warnings'],'runtime':r['runtime']}
        else: results[backend+'_actual_edit']={'status':'SKIPPED','reason':'Run scripts/first_demo.py --pipeline '+backend}
    (ROOT/'data/metadata/verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
    if any(r['status']=='FAIL' for r in results.values()): raise SystemExit(1)

if __name__=='__main__': main()
