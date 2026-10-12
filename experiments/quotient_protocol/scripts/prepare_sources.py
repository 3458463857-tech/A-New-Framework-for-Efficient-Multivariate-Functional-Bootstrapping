"""Copy only the scoped source snapshots; original workspaces stay immutable."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
V2=ROOT.parent
V1=V2.parent/'DCC_revision_2026-10-10_v1'
dest=ROOT/'source';dest.mkdir(exist_ok=True)
copies=[(V2/'baseline_experiments/source/refined-tfhe-lhe',dest/'refined-tfhe-lhe'),
        (V1/'05_Reproducibility/code/Section3_Code',dest/'section3')]
for src,out in copies:
    if out.exists(): raise SystemExit(f'Refusing existing source: {out}')
    shutil.copytree(src,out,ignore=shutil.ignore_patterns('target','build','.git','__pycache__'))
print('Source snapshots copied; no cryptography executed.')
