"""Audit exactly the Git index before publishing; never inspect ignored user data."""
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'models','envs','third_party','data','logs','dist','build','.venv'}
SECRETS=[re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'hf_[A-Za-z0-9]{25,}'),
         re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')]


def inspect_entry(name,data):
    problems=[]
    if Path(name).parts[0] in BLOCKED: problems.append('runtime/generated directory')
    if Path(name).name.startswith('.env') and Path(name).name!='.env.example': problems.append('environment secret file')
    if len(data)>10*1024*1024: problems.append('exceeds this source repository limit of 10 MiB')
    if any(p.search(data.decode('utf-8',errors='ignore')) for p in SECRETS): problems.append('possible credential; inspect locally')
    return problems


def audit():
    git=['git','-c','safe.directory='+ROOT.as_posix()]
    names=subprocess.check_output([*git,'ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    names=[n for n in names if n]; total=0; problems=[]
    if not names: raise RuntimeError('Nothing staged/tracked. Stage the source files first.')
    for name in names:
        data=subprocess.check_output([*git,'show',':'+name],cwd=ROOT)
        total+=len(data)
        problems += [name+': '+issue for issue in inspect_entry(name,data)]
    report={'files':len(names),'size_mib':round(total/2**20,3),'problems':problems}
    print(json.dumps(report,indent=2))
    if problems: raise SystemExit(1)
    return report

if __name__=='__main__': audit()
