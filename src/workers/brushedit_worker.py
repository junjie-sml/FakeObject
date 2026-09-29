import gc
import sys
from PIL import Image
import numpy as np
from src.system.paths import ROOT, config
from src.workers.common import serve, health, resize_for_inference

def handle(req):
    cfg=config('brushedit')
    base=ROOT/'models/brushedit'/cfg['base_subfolder']; brush=ROOT/'models/brushedit'/cfg['brushnet_subfolder']
    if req.get('action')=='health':
        result=health([('torch','torch'),('diffusers','diffusers'),('transformers','transformers')],[str(base/'model_index.json'),str(brush/'config.json')])
        try:
            from diffusers import StableDiffusionBrushNetPipeline, BrushNetModel
        except Exception as e: result['errors'].append(str(e)); result['status']='UNAVAILABLE'
        return result
    import torch
    from diffusers import StableDiffusionBrushNetPipeline, BrushNetModel, UniPCMultistepScheduler
    sys.path.insert(0,str(ROOT/'third_party/BrushEdit/app/src'))
    from brushedit_all_in_one_pipeline import BrushEdit_Pipeline
    if not torch.cuda.is_available(): raise RuntimeError('BRUSHEDIT UNAVAILABLE: CUDA-enabled PyTorch required for the tested profile.')
    image=Image.open(req['image']).convert('RGB'); mask=Image.open(req['mask']).convert('L')
    warnings=['Native BrushNetX inference; intent, target caption and SAM2 mask supplied by local orchestrator. Native BrushEdit VLM/SAM1 agent is not loaded.']
    for attempt in range(2):
        pipe=None; brushnet=None
        try:
            brushnet=BrushNetModel.from_pretrained(brush,torch_dtype=torch.float16,local_files_only=True)
            pipe=StableDiffusionBrushNetPipeline.from_pretrained(base,brushnet=brushnet,torch_dtype=torch.float16,low_cpu_mem_usage=True,local_files_only=True)
            pipe.scheduler=UniPCMultistepScheduler.from_config(pipe.scheduler.config)
            pipe.enable_vae_tiling(); pipe.enable_vae_slicing()
            if attempt: pipe.enable_sequential_cpu_offload()
            else: pipe.enable_model_cpu_offload()
            pipe.enable_attention_slicing('auto')
            size=int(req.get('max_side',512)) if not attempt else min(384,int(req.get('max_side',512)))
            small=resize_for_inference(image,size)
            small_mask=mask.resize(small.size,Image.Resampling.NEAREST)
            output=BrushEdit_Pipeline(pipe,req['prompt'],np.asarray(small_mask),np.asarray(small),torch.Generator('cpu').manual_seed(int(req.get('seed',42))),int(req.get('steps',20)),cfg['guidance_scale'],cfg['control_strength'],req.get('negative_prompt',''),1,False)[0][0]
            output=output.resize(image.size,Image.Resampling.LANCZOS)
            output.save(req['output'])
            return {'output':req['output'],'warnings':warnings,'inference_size':list(small.size),'model_ids':['TencentARC/BrushEdit/brushnetX','TencentARC/BrushEdit/'+cfg['base_subfolder']],'attempts':attempt+1}
        except RuntimeError as e:
            if 'out of memory' not in str(e).lower() or attempt: raise
            warnings.append('CUDA_OOM: retried once at reduced resolution with sequential CPU offload.')
        finally:
            del pipe, brushnet
            gc.collect(); torch.cuda.empty_cache()

if __name__=='__main__': serve(handle)
