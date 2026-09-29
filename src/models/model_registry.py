import json
from pathlib import Path
from src.system.paths import ROOT, config

MODELS = config('models')

def registry():
    result = []
    for name, entry in MODELS.items():
        path = ROOT/entry['path']; receipt = path/'download_receipt.json'
        saved = json.loads(receipt.read_text()) if receipt.exists() else {}
        complete=(saved.get('complete') and saved.get('revision')==entry['revision'] and saved.get('files')
                  and all((path/f).is_file() for f in saved['files']))
        result.append({**entry,'name':name,'local_path':str(path),
                       'download_status':'DOWNLOADED' if complete else 'MISSING_OR_PARTIAL',
                       'required_disk_bytes':saved.get('required_disk_bytes'),
                       'expected_revision':entry['revision'],'revision':saved.get('revision')})
    return result
