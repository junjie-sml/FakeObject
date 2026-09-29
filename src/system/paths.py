import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def setup_paths():
    for p in ['models', 'logs/workers', 'logs/runs', 'data/raw', 'data/test_images', 'data/demo_images', 'data/metadata', 'data/prompts', 'data/benchmarks', 'data/outputs', 'data/cache/ipc']:
        (ROOT / p).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('HF_HOME', str(ROOT / 'data/cache/huggingface'))
    os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
    os.environ.setdefault('GRADIO_TEMP_DIR', str(ROOT / 'data/cache/gradio'))
    os.environ.setdefault('PIP_CACHE_DIR', str(ROOT / 'data/cache/pip'))

def config(name):
    with (ROOT / 'configs' / f'{name}.yaml').open(encoding='utf-8') as f:
        return yaml.safe_load(f)

def python_for(name):
    return ROOT / 'envs' / name / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

setup_paths()
