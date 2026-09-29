import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from src.system.paths import ROOT, config
from src.system.hardware import detect_hardware
from src.system.model_manager import ModelManager
from src.system.logging import get_logger
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.schemas import FakeObjectSpec
from src.prompting.prompt_validator import validate_spec
from src.prompting.prompt_compiler import compile_prompt
from src.scene_analysis.analyzer import analyze_scene
from src.postprocessing.mask_processor import process_mask, mask_overlay, bbox_overlay
from src.postprocessing.compositor import strict_composite
from src.evaluation.metrics import evaluate
from src.pipelines.base import EditResult
from src.models.model_registry import registry
from src.prompting.language import grounding_phrase
from src.prompting.selected_region import describe_selected_region,bind_qwen_prompt

def load_image(image):
    if image is None: raise ValueError('Upload or select an image first.')
    try:
        im=image.copy() if isinstance(image,Image.Image) else Image.open(image)
        if im.width*im.height>config('app')['max_image_pixels']: raise ValueError('Image exceeds 25 megapixels; resize before loading.')
        return ImageOps.exif_transpose(im).convert('RGB')
    except (OSError,ValueError) as e: raise ValueError('Invalid image: '+str(e)) from e

def fingerprint(image): return hashlib.sha256(image.tobytes()+str(image.size).encode()).hexdigest()

def infer_target(instruction,target=None):
    if target and target.strip(): return target.strip()
    match=re.search(r'(?:replace|turn|make|change)\s+(?:only\s+)?(?:the\s+|this\s+|that\s+)?(.+?)\s+(?:with|into|to)\b',instruction,re.I)
    if match: return match.group(1).strip()
    match=re.search(r'(?:把|将)(.+?)(?:替换|变成|改成|换成)',instruction)
    if match: return match.group(1).strip()
    match=re.search(r'(?:替换|更换)(.+?)(?:为|成|，|。|$)',instruction)
    if match: return match.group(1).strip()
    raise ValueError('Could not identify the target locally. Enter a short target phrase, e.g. mug / cup.')

def new_run():
    now=datetime.now(timezone.utc)
    folder=ROOT/'data/outputs'/now.strftime('%Y-%m-%d')/(now.strftime('%H%M%S')+'-'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    return folder

def detect(image,target,threshold=None,search_mode='standard',max_candidates=None,extra_queries='',deduplicate=True):
    im=load_image(image); folder=new_run(); im.save(folder/'original.png')
    phrase=grounding_phrase(target)
    cfg=config('grounded_sam')
    threshold=float(threshold if threshold is not None else cfg['broad_threshold'] if search_mode=='broad' else cfg['threshold'])
    limit=int(max_candidates if max_candidates is not None else cfg['broad_max_candidates'] if search_mode=='broad' else cfg['max_candidates'])
    result=ModelManager().run('grounded_sam',{'action':'detect','image':str(folder/'original.png'),'target':phrase,
        'threshold':threshold,'output_dir':str(folder),'search_mode':search_mode,'max_candidates':limit,
        'extra_queries':extra_queries,'deduplicate':deduplicate})
    result['grounding_prompt']=phrase
    result.update(image_hash=fingerprint(im),target=target,output_dir=str(folder),original_image=str(folder/'original.png'))
    overlay=bbox_overlay(im,result['boxes'],result['labels'],result['scores']); overlay.save(folder/'bbox_overlay.png')
    result['bbox_visualization']=str(folder/'bbox_overlay.png')
    previews=[]
    for i,(box,path) in enumerate(zip(result['boxes'],result['masks'])):
        x1,y1,x2,y2=box; padding=max(8,int(max(x2-x1,y2-y1)*.15))
        region=(max(0,int(x1)-padding),max(0,int(y1)-padding),min(im.width,int(x2)+padding),min(im.height,int(y2)+padding))
        crop=im.crop(region); crop.thumbnail((320,240))
        with Image.open(path) as candidate:
            mask_crop=candidate.convert('L').crop(region).resize(crop.size,Image.Resampling.NEAREST)
        preview=folder/f'candidate_{i}_preview.png'; mask_overlay(crop,mask_crop).save(preview)
        previews.append(str(preview))
    result['candidate_previews']=previews
    (folder/'detection.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result

def select_mask(detection,instance=None):
    if not detection or not detection.get('masks'): raise ValueError('No mask available. Detect the target first.')
    if instance is None:
        if len(detection['masks'])!=1: raise ValueError('MULTIPLE_DETECTIONS: choose an instance before editing.')
        instance=0
    instance=int(instance)
    if not 0<=instance<len(detection['masks']): raise ValueError('Selected instance is out of range.')
    return Image.open(detection['masks'][instance]).convert('L')

def run_edit(image,pipeline,user_prompt,target_object=None,target_instance=None,seed=42,
             strict_preservation=True,quality_profile='preview',detection=None,spec=None,backend_prompt=None,
             mask_settings=None,occluder_mask=None,steps=None,prompt_mode='autonomous',**kwargs):
    start=time.perf_counter(); im=load_image(image); target=infer_target(user_prompt,target_object)
    if pipeline != 'qwen_image': raise ValueError('Unknown pipeline.')
    folder=new_run(); original=folder/'original.png'; im.save(original)
    result=EditResult(run_id=folder.name,pipeline=pipeline,status='PARTIALLY READY',output_dir=str(folder),original_image=str(original),target_object=target,raw_user_prompt=user_prompt,seed=int(seed),hardware_stats=detect_hardware())
    settings={'mask_dilation_px':None,'mask_dilation_ratio':.02,'mask_feather_px':3,'cleanup_min_component':32,'erosion_px':0,'fill_holes':True,**(mask_settings or {})}; generation={}
    try:
        t=time.perf_counter()
        if detection:
            if detection.get('image_hash')!=fingerprint(im) or detection.get('target')!=target:
                raise ValueError('Image or target changed after detection; detect again before editing.')
        else: detection=detect(im,target)
        result.grounding_result=detection
        raw=select_mask(detection,target_instance)
        target_instance=0 if target_instance is None else int(target_instance)
        result.selected_region=describe_selected_region(detection,target_instance,raw)
        hard,alpha=process_mask(raw,preserve_occluders=occluder_mask,**settings)
        for name,img in [('raw_mask',raw),('processed_mask',hard),('alpha_mask',alpha),('mask_overlay',mask_overlay(im,hard)),('bbox_overlay',bbox_overlay(im,detection['boxes'],detection['labels'],detection['scores']))]: img.save(folder/f'{name}.png')
        result.raw_mask=str(folder/'raw_mask.png'); result.processed_mask=str(folder/'processed_mask.png'); result.mask_visualization=str(folder/'mask_overlay.png'); result.bbox_visualization=str(folder/'bbox_overlay.png')
        result.scene_analysis=analyze_scene(im,raw,target)
        result.runtime['grounding_mask']=round(time.perf_counter()-t,3)
        if spec is None: spec=generate_concepts(user_prompt,target,result.scene_analysis,seed=seed,mode=prompt_mode)[0]
        elif not isinstance(spec,FakeObjectSpec): spec=FakeObjectSpec.model_validate(spec)
        if spec.target_object!=target: raise ValueError('Concept target differs from detected target; regenerate concepts.')
        if spec.raw_user_prompt!=user_prompt: raise ValueError('Instruction changed after concept creation; regenerate concepts or update raw_user_prompt in the JSON.')
        validate_spec(spec)
        result.fake_object_spec=spec.model_dump(); result.polished_prompt=compile_prompt(spec,'qwen_image'); result.backend_prompt=backend_prompt or compile_prompt(spec,pipeline)
        if pipeline=='qwen_image':
            # Recompile unchanged prompts saved by older app versions, while
            # preserving explicitly edited backend text.
            if not backend_prompt or backend_prompt==spec.final_edit_prompt:
                result.backend_prompt=compile_prompt(spec,pipeline)
            result.backend_prompt=bind_qwen_prompt(result.backend_prompt,user_prompt,result.selected_region)
        result.negative_prompt=spec.negative_prompt
        result.warnings+=spec.warnings+result.scene_analysis['warnings']
        thresholds=config('novelty_rules')['thresholds']
        if any(getattr(spec.scores,key+'_score')<value for key,value in thresholds.items()):
            raise ValueError('Prompt validation below threshold; revise the concept JSON before generation. '+ '; '.join(spec.warnings))
        (folder/'prompt.txt').write_text(result.backend_prompt,encoding='utf-8')
        size={'preview':512,'balanced':768,'high':1024}[quality_profile]
        default_steps=config('qwen_image')['steps']
        generation={'max_side':size,'steps':int(steps or default_steps),'quality':quality_profile,'strict_preservation':strict_preservation}
        response=ModelManager().run(pipeline,{'action':'edit','image':str(original),'mask':result.processed_mask,'prompt':result.backend_prompt,'negative_prompt':spec.negative_prompt,'seed':int(seed),'output':str(folder/'raw_output.png'),**generation},timeout=config('app')['worker_timeout'])
        generated=Image.open(response['output']).convert('RGB')
        strict=strict_composite(im,generated,alpha); strict.save(folder/'strict_output.png')
        (strict if strict_preservation else generated).save(folder/'final_output.png')
        result.raw_model_output=response['output']; result.strict_output=str(folder/'strict_output.png')
        result.evaluation={'raw':evaluate(im,generated,hard),'strict':evaluate(im,strict,hard)}
        if (ROOT/'models/clip/download_receipt.json').exists():
            try:
                diagnostic=ModelManager().run('grounded_sam',{'action':'evaluate','image':str(original),'output':result.strict_output,'mask':result.processed_mask,'target':target})
                result.evaluation['category_diagnostics']=diagnostic['category_diagnostics']
                result.runtime['category_evaluation']=diagnostic['runtime']
            except Exception as e:
                result.warnings.append('Optional category evaluation failed: '+str(e))
        result.runtime['generation']=response['runtime']; result.hardware_stats['peak_gpu_memory_mb']=response.get('peak_gpu_memory_mb')
        result.warnings+=response.get('warnings',[]); result.model_versions['inference']=response.get('model_ids')
        generation['worker_response']=response
        result.status='READY'
    except Exception as e:
        result.warnings.append(str(e)); get_logger().exception(f'run_failed id={result.run_id}')
        result.status='PARTIALLY READY'
    finally:
        result.runtime['total']=round(time.perf_counter()-start,3)
        result.model_versions.update(registry=registry())
        repo_path=ROOT/'data/metadata/repository_versions.json'
        result.model_versions['repositories']=json.loads(repo_path.read_text(encoding='utf-8')) if repo_path.exists() else []
        metadata=result.model_dump(); metadata.update(timestamp=datetime.now(timezone.utc).isoformat(),synthetic_edit=True,mask_settings=settings,generation_parameters=generation,selected_instance=target_instance)
        software=ROOT/'data/metadata/environment_versions.json'
        metadata['software_versions']=json.loads(software.read_text()) if software.exists() else {}
        (folder/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        (folder/'logs.txt').write_text('\n'.join(result.warnings),encoding='utf-8')
    return result
