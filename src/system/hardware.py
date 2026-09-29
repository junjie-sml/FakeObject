"""Non-destructive hardware probing; importing the UI never imports torch."""
import csv
import io
import platform
import re
import subprocess
import psutil

def detect_hardware(include_torch=False):
    result = {'os': platform.platform(), 'python': platform.python_version(), 'gpus': [],
              'ram_gb': round(psutil.virtual_memory().total / 2**30, 2), 'profile': 'CPU', 'warnings': []}
    try:
        out = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version', '--format=csv,noheader,nounits'], text=True, timeout=10)
        for row in csv.reader(io.StringIO(out)):
            name, total, free, driver = [v.strip() for v in row]
            result['gpus'].append(dict(name=name, total_vram_mb=int(total), free_vram_mb=int(free), driver=driver))
        result['profile'] = 'LOW_VRAM' if int(total) < 16000 else 'STANDARD' if int(total) < 24000 else 'HIGH_VRAM'
        full = subprocess.check_output(['nvidia-smi'], text=True, timeout=10)
        match = re.search(r'CUDA(?: UMD)? Version:\s*([\d.]+)', full)
        result['driver_cuda_max'] = match.group(1) if match else None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        result['warnings'].append(f'NVIDIA probe unavailable: {e}')
    if include_torch:
        try:
            import torch
            result.update(torch=torch.__version__, torch_cuda_runtime=torch.version.cuda, cuda_available=torch.cuda.is_available())
            if torch.cuda.is_available():
                x = torch.ones(1, device='cuda') + 1
                result['cuda_compute_test'] = x.item() == 2
                result['bf16_supported'] = torch.cuda.is_bf16_supported()
        except Exception as e:
            result['warnings'].append(f'PyTorch probe: {e}')
    return result
