import gc
import json
import sys
import time
import traceback
from pathlib import Path
from src.system.paths import ROOT

def serve(handler):
    request_path, response_path = map(Path, sys.argv[1:3])
    request = json.loads(request_path.read_text(encoding='utf-8'))
    start = time.perf_counter()
    try:
        result = handler(request)
        result.update(ok=True, worker_seconds=round(time.perf_counter()-start,3))
    except Exception as e:
        traceback.print_exc()
        msg = str(e)
        if 'out of memory' in msg.lower():
            msg = 'CUDA_OOM: inference exceeded memory after one safer retry. Try preview resolution; close other GPU jobs. '+msg
        result = {'ok':False,'error':f'{type(e).__name__}: {msg}','worker_seconds':round(time.perf_counter()-start,3)}
    finally:
        gc.collect()
        if 'torch' in sys.modules:
            import torch
            if torch.cuda.is_available():
                result['peak_gpu_memory_mb'] = round(torch.cuda.max_memory_allocated()/2**20,1)
                torch.cuda.empty_cache()
    response_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

def health(dependencies, model_paths):
    from importlib import import_module, metadata
    from src.system.hardware import detect_hardware
    errors=[]; versions={}
    for module, dist in dependencies:
        try:
            import_module(module); versions[dist]=metadata.version(dist)
        except Exception as e:
            errors.append(f'{module}: {e}')
    for path in model_paths:
        if not (ROOT/path).exists(): errors.append('Missing '+str(ROOT/path))
    return {'status':'UNAVAILABLE' if errors else 'PARTIALLY READY', 'errors':errors,'software':versions,'hardware':detect_hardware(True), 'note':'Health verifies imports and files; READY requires successful saved inference.'}

def resize_for_inference(image, max_side, multiple=8, allow_upscale=False):
    from PIL import Image
    scale = max_side/max(image.size)
    if not allow_upscale: scale=min(1,scale)
    size=tuple(max(multiple, int(n*scale)//multiple*multiple) for n in image.size)
    return image.resize(size,Image.Resampling.LANCZOS)
