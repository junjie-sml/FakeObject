"""Small COCO validation subset with per-image original licenses and attribution links."""
import argparse
import concurrent.futures
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from PIL import Image
from src.system.paths import ROOT

def fetch(url,path):
    if path.exists(): return
    temp=path.with_suffix(path.suffix+'.part')
    with requests.get(url,stream=True,timeout=(30,180)) as response:
        response.raise_for_status()
        with temp.open('wb') as f:
            for chunk in response.iter_content(1024*1024): f.write(chunk)
    temp.replace(path)

def collect(count=50):
    archive=ROOT/'data/raw/annotations_trainval2017.zip'
    fetch('https://s3.amazonaws.com/images.cocodataset.org/annotations/annotations_trainval2017.zip',archive)
    with zipfile.ZipFile(archive) as z:
        data=json.loads(z.read('annotations/instances_val2017.json'))
    categories={x['id']:x['name'] for x in data['categories']}; licenses={x['id']:x for x in data['licenses']}
    annotations={}; areas={}
    for ann in data['annotations']:
        annotations.setdefault(ann['image_id'],[]).append(categories[ann['category_id']])
        key=(ann['image_id'],categories[ann['category_id']]); areas[key]=max(areas.get(key,0),ann['area'])
    images={x['id']:x for x in data['images']}
    targets=['cup','bottle','chair','backpack','cell phone','keyboard','vase','book','shoe','bowl','laptop','wine glass','remote','handbag','clock']
    # Prefer clear targets and licenses allowing derivatives; record exact terms regardless.
    pools={t:sorted([i for i in images if t in annotations.get(i,[]) and images[i]['license'] in [1,2,4,5,7]],key=lambda i: -areas.get((i,t),0)/(images[i]['width']*images[i]['height'])) for t in targets}
    selected=[]; primary_targets={}
    for n in range(count):
        available=next((t for t in targets[n%len(targets):]+targets[:n%len(targets)] if any(i not in selected for i in pools[t])),None)
        if available is None: break
        selected.append(next(i for i in pools[available] if i not in selected))
        primary_targets[selected[-1]]=available
    def one(ident):
        entry=images[ident]; lic=licenses[entry['license']]; dest=ROOT/'data/test_images'/entry['file_name']
        url=entry['coco_url'].replace('http://images.cocodataset.org/','https://s3.amazonaws.com/images.cocodataset.org/').replace('https://images.cocodataset.org/','https://s3.amazonaws.com/images.cocodataset.org/')
        try:
            fetch(url,dest)
            with Image.open(dest) as im: im.verify()
            record={'local_path':dest.relative_to(ROOT).as_posix(),'source_dataset':'COCO val2017','source_page':entry.get('flickr_url',url),'download_url':url,'original_identifier':ident,'license':lic['name'],'license_url':lic['url'],'attribution':entry.get('flickr_url','See source page for original creator'),'download_date':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'width':entry['width'],'height':entry['height'],'candidate_objects':sorted(set(annotations[ident])),'licensing_status':'TEST_ONLY','notes':'Original photo license applies. Training eligibility has not been reviewed.'}
            record['primary_target']=primary_targets[ident]
            return record
        except Exception as e:
            print(f'Image {ident}: {e}',flush=True); return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records=[r for r in pool.map(one,selected) if r]
    manifest=ROOT/'data/metadata/image_manifest.jsonl'
    manifest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    import shutil
    for r in records[:10]:
        shutil.copy2(ROOT/r['local_path'],ROOT/'data/demo_images'/Path(r['local_path']).name)
    print(f'Collected {len(records)} photos; {min(10,len(records))} demo shortlist. Manifest: {manifest}')
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--count',type=int,default=50); collect(p.parse_args().count)
