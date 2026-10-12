"""Bind the final type-correct source and copied input manifests without changing trials."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V5=ROOT.parent;WORK=V5.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=ROOT/'provenance/source_derivation.json';record=json.loads(p.read_text())
record['initial_generated_sha256']=record.get('initial_generated_sha256',record['derived_sha256'])
record['derived_sha256']=sha(ROOT/'ours/src/bin/functions_checked.rs')
record['compile_repair']='Cast the expected PBS count from usize to u64 in an assertion; no circuit change. Both build snapshots retained.'
p.write_text(json.dumps(record,indent=2)+'\n')
files=[]
for inp in sorted((ROOT/'inputs').glob('*.csv')):
    origin=(WORK/'DCC_submission_polish_v4/experiments_functions/inputs' if inp.stem in ['hamming_interval10','set_interval4_6','set_threshold4_6'] else V5/'experiments_small_functions/inputs')/inp.name
    assert inp.read_bytes()==origin.read_bytes()
    files.append(dict(task_id=inp.stem,sha256=sha(inp),original=str(origin.relative_to(WORK)),rows=35))
record=dict(files=files,copy_binding='PASS',large_definitions_sha256=sha(ROOT/'scripts/large_task_definitions.py'),small_definitions_sha256=sha(ROOT/'scripts/small_task_definitions.py'))
(ROOT/'inputs/manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: exact final source and ten original input files bound')
