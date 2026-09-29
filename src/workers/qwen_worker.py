import gc
import inspect
from PIL import Image
from src.system.paths import ROOT, config
from src.workers.common import serve, health, resize_for_inference
from src.postprocessing.qwen_conditioning import mask_references
from pathlib import Path


def configure_condition_processor(processor):
    # QwenImage21Pipeline already resizes each reference to multiples of 32 and
    # sends that same size to the VAE and vision encoder. The processor's default
    # min_pixels resize can enlarge small references a second time (288x224 ->
    # 320x256), creating more image slots than VAE latents. Keep the shared grid.
    processor.image_processor.do_resize=False


class QwenImageEditor:
    def __init__(self): self.pipe=None
    def health_check(self):
        result=health([('torch','torch'),('diffusers','diffusers'),('transformers','transformers')],['models/qwen_image/model_index.json'])
        try:
            from diffusers import QwenImage21Pipeline
            result['signature']=str(inspect.signature(QwenImage21Pipeline.__call__))
        except Exception as e:
            result['errors'].append('QWEN BACKEND UNAVAILABLE: '+str(e)); result['status']='UNAVAILABLE'
        return result
    def load(self, offload='sequential'):
        import torch
        from diffusers import QwenImage21Pipeline
        if not torch.cuda.is_available(): raise RuntimeError('QWEN BACKEND UNAVAILABLE: CUDA PyTorch required.')
        dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        self.pipe=QwenImage21Pipeline.from_pretrained(ROOT/'models/qwen_image',torch_dtype=dtype,local_files_only=True,low_cpu_mem_usage=True)
        configure_condition_processor(self.pipe.processor)
        if hasattr(self.pipe,'enable_vae_tiling'): self.pipe.enable_vae_tiling()
        if hasattr(self.pipe,'enable_vae_slicing'): self.pipe.enable_vae_slicing()
        if offload=='sequential': self.pipe.enable_sequential_cpu_offload()
        else: self.pipe.enable_model_cpu_offload()
    def unload(self):
        import torch
        self.pipe=None; gc.collect(); torch.cuda.empty_cache()
    def edit(self,req):
        import torch
        image=Image.open(req['image']).convert('RGB'); mask=Image.open(req['mask']).convert('RGB')
        warnings=[]
        for attempt in range(2):
            try:
                self.load('sequential')
                small=resize_for_inference(image,min(384,int(req.get('max_side',512))) if attempt else int(req.get('max_side',512)),32,allow_upscale=True)
                params=inspect.signature(self.pipe.__call__).parameters
                kwargs={'prompt':req['prompt'],'image':small,'num_inference_steps':int(req.get('steps',config('qwen_image')['steps'])),'generator':torch.Generator('cpu').manual_seed(int(req.get('seed',42))),'width':small.width,'height':small.height}
                if 'output_resolution' in params: kwargs['output_resolution']=max(small.size)
                guidance=float(config('qwen_image').get('true_cfg_scale',1.0))
                if guidance>1 and 'true_cfg_scale' in params and 'negative_prompt' in params:
                    kwargs.update(true_cfg_scale=guidance,negative_prompt=req.get('negative_prompt',''))
                if 'mask_image' in params:
                    kwargs['mask_image']=mask.resize(small.size,Image.Resampling.NEAREST)
                else:
                    resized_mask=mask.resize(small.size,Image.Resampling.NEAREST)
                    strategy=req.get('mask_strategy',config('qwen_image').get('mask_strategy','source_scope'))
                    if strategy=='source_scope':
                        kwargs['image']=small
                        kwargs['prompt']=req['prompt']
                        warnings.append('Qwen uses the source photograph and selected scope instructions; final compositing enforces the selected mask.')
                    elif strategy=='separate_reference_mask':
                        kwargs['image'],kwargs['prompt']=mask_references(small,resized_mask,req['prompt'])
                        warnings.append('Qwen uses a separate mask reference; strict localization is enforced by final compositing.')
                    else: raise ValueError('Unknown Qwen mask strategy: '+strategy)
                Path(req['output']).with_name('conditioning_prompt.txt').write_text(kwargs['prompt'],encoding='utf-8')
                output=self.pipe(**kwargs).images[0].convert('RGB').resize(image.size,Image.Resampling.LANCZOS)
                output.save(req['output'])
                return {'output':req['output'],'warnings':warnings,'inference_size':list(small.size),'condition_resize':'pipeline_only','mask_strategy':strategy if 'mask_image' not in params else 'native','model_ids':['Qwen/Qwen-Image-2.1'],'attempts':attempt+1,'true_cfg_scale':guidance,'negative_prompt_mode':'native' if guidance>1 else 'natural-language constraints'}
            except RuntimeError as e:
                if 'out of memory' not in str(e).lower() or attempt: raise
                warnings.append('CUDA_OOM: one reduced-resolution sequential-offload retry.')
            finally: self.unload()

def handle(req):
    editor=QwenImageEditor()
    return editor.health_check() if req.get('action')=='health' else editor.edit(req)

if __name__=='__main__': serve(handle)
