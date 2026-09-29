"""Fetch the exact audited upstream commits; never replace an existing checkout."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPOS=json.loads((ROOT/'configs/repositories.json').read_text(encoding='utf-8'))


def ensure_repo(name):
    entry=REPOS[name]; folder=ROOT/'third_party'/name
    def git(*args):
        return subprocess.check_output(['git','-c','safe.directory='+folder.as_posix(),'-C',str(folder),*args],text=True).strip()
    if not folder.exists():
        folder.mkdir(parents=True)
        git('init')
        git('remote','add','origin',entry['url'])
    # A failed download can be retried; a different/modified checkout is left intact.
    try: head=git('rev-parse','--verify','HEAD')
    except subprocess.CalledProcessError: head=None
    if head is not None and head!=entry['revision']:
        raise RuntimeError(f'{folder} is at {head}, expected {entry["revision"]}. Keep any local work and use a fresh project checkout.')
    if git('status','--porcelain'):
        raise RuntimeError(f'{folder} has local changes; use an unmodified dependency checkout.')
    if head is None:
        git('fetch','--depth','1','origin',entry['revision'])
        git('checkout','--detach',entry['revision'])
    return {'name':name,'remote':git('remote','get-url','origin'),'commit':git('rev-parse','HEAD'),
            'dirty':False,'checked_at':datetime.now(timezone.utc).isoformat(),
            'license_file':str(folder/'LICENSE')}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',choices=[*REPOS,'all'],default='all')
    args=parser.parse_args()
    path=ROOT/'data/metadata/repository_versions.json'; path.parent.mkdir(parents=True,exist_ok=True)
    existing=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    records={r['name']:r for r in existing if r['name'] in REPOS}
    for name in REPOS if args.repo=='all' else [args.repo]:
        records[name]=ensure_repo(name)
        print(f'{name}: {records[name]["commit"]}')
    path.write_text(json.dumps(list(records.values()),indent=2),encoding='utf-8')

if __name__=='__main__': main()
