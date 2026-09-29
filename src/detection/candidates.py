"""Bounded query expansion and conservative box deduplication, without GPU imports."""
import re
import numpy as np
from src.prompting.language import grounding_phrase


RELATED_NAMES={
    'building':['building facade','tower','architectural structure'],
    'house':['building','house facade'],
    'tower':['building tower','turret'],
    'cup':['mug','drinking cup','glass'],
    'mug':['cup','coffee mug'],
    'bottle':['water bottle','glass bottle'],
    'chair':['seat','armchair'],
    'backpack':['rucksack','backpack bag'],
    'cell phone':['mobile phone','smartphone'],
    'lamp':['table lamp','light fixture'],
    'vase':['flower vase'],
    'keyboard':['computer keyboard'],
}


def detection_queries(target,mode='standard',extra_queries=''):
    if mode not in ('standard','broad'):
        raise ValueError('Unknown detection search mode.')
    primary=grounding_phrase(target).lower().strip().rstrip('.')
    if not primary:
        raise ValueError('Specify a target object or use a replacement instruction naming the target.')
    queries=[primary]
    if mode=='broad':
        queries.extend(RELATED_NAMES.get(primary,[]))
    queries.extend(grounding_phrase(q).lower().strip().rstrip('.')
                   for q in re.split(r'[,，;；\n]+',extra_queries or '') if q.strip())
    queries=list(dict.fromkeys(q for q in queries if q))
    if len(queries)>12:
        raise ValueError('最多使用 12 个检测名称，请减少补充名称。')
    return queries


def box_iou(a,b):
    a=np.asarray(a); b=np.asarray(b)
    intersection=np.maximum(0,np.minimum(a[2:],b[2:])-np.maximum(a[:2],b[:2])).prod()
    area_a=(a[2:]-a[:2]).prod(); area_b=(b[2:]-b[:2]).prod()
    return float(intersection/max(float(area_a+area_b-intersection),1e-9))


def select_candidates(records,image_size,max_candidates=50,deduplicate=True,iou_threshold=.9):
    """Merge only near-identical boxes. Contained local/whole-object alternatives survive."""
    limit=int(max_candidates)
    if not 1<=limit<=100:
        raise ValueError('候选数量上限必须在 1–100 之间。')
    width,height=image_size
    valid=[]
    for record in records:
        box=np.asarray(record['box'],dtype=float)
        score=float(record['score'])
        if box.shape!=(4,) or not np.isfinite(box).all() or not np.isfinite(score): continue
        box=np.clip(box,[0,0,0,0],[width,height,width,height])
        if box[2]<=box[0] or box[3]<=box[1]: continue
        valid.append({**record,'box':box.tolist(),'score':score,'queries':[record['query']]})
    unique=[]
    for record in sorted(valid,key=lambda r:r['score'],reverse=True):
        duplicate=next((r for r in unique if box_iou(r['box'],record['box'])>=iou_threshold),None) if deduplicate else None
        if duplicate is None:
            unique.append(record)
        elif record['query'] not in duplicate['queries']:
            duplicate['queries'].append(record['query'])
    return unique[:limit],{
        'raw_count':len(records),'valid_count':len(valid),'unique_count':len(unique),
        'returned_count':min(len(unique),limit),'duplicate_count':len(valid)-len(unique),
        'truncated_count':max(0,len(unique)-limit),'max_candidates':limit,
        'deduplicate':bool(deduplicate),'duplicate_iou':iou_threshold if deduplicate else None,
    }
