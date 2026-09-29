"""Canonical launcher re-execs into the isolated orchestrator environment."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
python=ROOT/'envs/orchestrator'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists(): raise SystemExit('Run python scripts/bootstrap.py first.')
if Path(sys.executable).resolve()!=python.resolve():
    import subprocess
    raise SystemExit(subprocess.call([str(python),str(Path(__file__).resolve()),*sys.argv[1:]],cwd=ROOT))
sys.path.insert(0,str(ROOT))
from src.ui.app import main
main()
