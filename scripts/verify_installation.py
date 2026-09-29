import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.system.paths import python_for
from src.system.hardware import detect_hardware
from src.system.model_manager import ModelManager

def verify():
    report={'hardware':detect_hardware(),'workers':{}}
    versions={}
    for name in ['orchestrator','grounded_sam','brushedit','qwen_image']:
        py=python_for(name)
        if not py.exists(): versions[name]={'error':'Environment not created'}; continue
        try:
            frozen=subprocess.check_output([str(py),'-m','pip','freeze'],text=True,timeout=60)
            (ROOT/'envs'/name/'requirements.lock.txt').write_text(frozen,encoding='utf-8')
            versions[name]={'python':str(py),'packages':frozen.splitlines()}
            if name!='orchestrator': report['workers'][name]=ModelManager().run(name,{'action':'health'},timeout=120)
        except Exception as e: report['workers'][name]={'status':'UNAVAILABLE','error':str(e)}
    (ROOT/'data/metadata/environment_versions.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
    (ROOT/'data/metadata/health.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2)); return report

if __name__=='__main__': verify()
