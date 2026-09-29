"""One-shot JSON workers: process exit releases all models, cross-process GPU lock."""
import json
import os
import subprocess
import time
import uuid
from filelock import FileLock, Timeout
from src.system.paths import ROOT, python_for
from src.system.logging import get_logger

class WorkerError(RuntimeError):
    pass

class ModelManager:
    def __init__(self):
        self.state = 'NONE'
        self.lock = FileLock(str(ROOT / 'data/cache/gpu.lock'))

    def run(self, worker, payload, timeout=1800):
        modules = {'grounded_sam': 'grounded_sam_worker', 'qwen_image': 'qwen_worker'}
        if worker not in modules: raise WorkerError('Unsupported worker: ' + worker)
        py = python_for(worker)
        if not py.exists():
            raise WorkerError(f'{worker.upper()} UNAVAILABLE: run python scripts/create_envs.py --worker {worker}')
        ident = uuid.uuid4().hex
        req = ROOT / 'data/cache/ipc' / f'{ident}.request.json'
        res = req.with_name(f'{ident}.response.json')
        req.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        log = ROOT / 'logs/workers' / f'{worker}-{ident}.log'
        module = modules[worker]
        started = time.perf_counter()
        try:
            with self.lock.acquire(timeout=30):
                self.state = worker.upper() + '_LOADED'
                get_logger().info(f'stage_start worker={worker} request={ident}')
                env = os.environ.copy()
                env['PYTHONPATH'] = str(ROOT)
                env['HF_HUB_OFFLINE'] = '1'
                env['TRANSFORMERS_OFFLINE'] = '1'
                env['PYTHONUTF8'] = '1'
                with log.open('w', encoding='utf-8') as output:
                    process = subprocess.run([str(py), '-m', f'src.workers.{module}', str(req), str(res)], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
                if not res.exists():
                    raise WorkerError(f'{worker} worker exited ({process.returncode}). Details: {log}')
                response = json.loads(res.read_text(encoding='utf-8'))
                if not response.get('ok'):
                    raise WorkerError(response.get('error', 'Worker failed') + f' | Log: {log}')
                response['runtime'] = round(time.perf_counter() - started, 3)
                return response
        except Timeout as e:
            raise WorkerError('GPU is busy with another application request. Wait for it to finish.') from e
        except subprocess.TimeoutExpired as e:
            raise WorkerError(f'{worker} timed out after {timeout}s; worker terminated. Log: {log}') from e
        finally:
            self.state = 'NONE'
            get_logger().info(f'stage_end worker={worker} seconds={time.perf_counter()-started:.3f}')

    def unload(self):
        # Workers are not retained after a request.
        self.state = 'NONE'
