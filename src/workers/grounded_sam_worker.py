import gc
import inspect
from pathlib import Path
import numpy as np
from PIL import Image
from src.system.paths import ROOT, config
from src.workers.common import serve, health
from src.detection.candidates import detection_queries, select_candidates

def handle(req):
    if req.get('action') == 'evaluate':
        from src.evaluation.category_diagnostics import classify_crop
        return {'category_diagnostics':classify_crop(req)}
    if req.get('action') == 'health':
        return health([('torch','torch'),('transformers','transformers'),('sam2','SAM-2')],['models/grounding_dino/config.json','models/sam2/sam2.1_hiera_tiny.pt'])
    import torch
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    cfg=config('grounded_sam'); device='cuda' if torch.cuda.is_available() and not req.get('force_cpu') else 'cpu'
    image=Image.open(req['image']).convert('RGB')
    mode=req.get('search_mode','standard')
    queries=detection_queries(req['target'],mode,req.get('extra_queries',''))
    threshold=float(req.get('threshold',cfg['broad_threshold'] if mode=='broad' else cfg['threshold']))
    if not .01<=threshold<=1: raise ValueError('检测阈值必须在 0.01–1 之间。')
    folder=Path(req['output_dir']); folder.mkdir(parents=True,exist_ok=True)
    processor=AutoProcessor.from_pretrained(ROOT/'models/grounding_dino',local_files_only=True)
    model=AutoModelForZeroShotObjectDetection.from_pretrained(ROOT/'models/grounding_dino',local_files_only=True).to(device)
    params=inspect.signature(processor.post_process_grounded_object_detection).parameters
    threshold_key='threshold' if 'threshold' in params else 'box_threshold'
    records=[]
    # Query separately so a strong match for one phrase cannot hide alternatives.
    # Keep one DINO load, then release it before loading SAM.
    for phrase in queries:
        inputs=processor(images=image,text=phrase+'.',return_tensors='pt').to(device)
        with torch.inference_mode(): outputs=model(**inputs)
        detected=processor.post_process_grounded_object_detection(outputs,inputs.input_ids,
            **{threshold_key:threshold},text_threshold=min(cfg['text_threshold'],threshold),target_sizes=[image.size[::-1]])[0]
        boxes=detected['boxes'].cpu().tolist(); scores=detected['scores'].cpu().tolist()
        labels=detected.get('text_labels',detected.get('labels',['']*len(boxes)))
        records.extend({'box':box,'score':score,'label':str(label).strip() or phrase,'query':phrase}
                       for box,score,label in zip(boxes,scores,labels))
        del inputs, outputs, detected
    del model
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    candidates,stats=select_candidates(records,image.size,
        req.get('max_candidates',cfg['broad_max_candidates'] if mode=='broad' else cfg['max_candidates']),
        req.get('deduplicate',True),cfg['duplicate_iou'])
    search={'mode':mode,'queries':queries,'threshold':threshold,**stats}
    if not candidates:
        return {'boxes':[],'scores':[],'labels':[],'masks':[],'selected_instance':None,'search':search,
                'warnings':['NO_DETECTIONS: try a simpler English noun or lower the threshold.']}
    boxes=np.array([r['box'] for r in candidates],dtype=np.float32)
    labels=[r['label'] for r in candidates]; scores=[r['score'] for r in candidates]
    sam=build_sam2(cfg['sam_config'],str(ROOT/'models/sam2/sam2.1_hiera_tiny.pt'),device=device,apply_postprocessing=False)
    predictor=SAM2ImagePredictor(sam)
    paths=[]; all_sam_scores=[]
    with torch.inference_mode():
        predictor.set_image(np.asarray(image))
        for start in range(0,len(boxes),cfg['sam_batch_size']):
            masks,sam_scores,_=predictor.predict(point_coords=None,point_labels=None,
                box=boxes[start:start+cfg['sam_batch_size']],multimask_output=False)
            if masks.ndim==4: masks=masks[:,0]
            if masks.ndim==2: masks=masks[None]
            for j,mask in enumerate(masks):
                p=folder/f'candidate_{start+j}.png'
                Image.fromarray((mask>0).astype('uint8')*255).save(p); paths.append(str(p))
            all_sam_scores.extend(np.asarray(sam_scores).reshape(-1).tolist())
    warnings=['Multiple objects found: select an instance explicitly.'] if len(paths)>1 else []
    if stats['truncated_count']:
        warnings.append(f"达到候选上限，另有 {stats['truncated_count']} 个候选未展示；可提高候选数量上限后重新检测。")
    return {'boxes':boxes.tolist(),'scores':scores,'labels':labels,'masks':paths,'selected_instance':0 if len(paths)==1 else None,
            'sam_scores':all_sam_scores,'warnings':warnings,'search':search,'candidate_queries':[r['queries'] for r in candidates],
            'model_ids':['IDEA-Research/grounding-dino-tiny','facebook/sam2.1-hiera-tiny'],'device':device}

def guarded(req):
    try: return handle(req)
    except RuntimeError as e:
        if 'out of memory' not in str(e).lower() or req.get('action')=='health': raise
        import torch
        gc.collect(); torch.cuda.empty_cache()
        # Release the failed stack before retrying the same models on CPU.
        e.__traceback__=None
        gc.collect(); torch.cuda.empty_cache()
        result=handle({**req,'force_cpu':True})
        result.setdefault('warnings',[]).append('CUDA_OOM: same grounding models retried once on CPU.')
        return result

if __name__=='__main__': serve(guarded)
