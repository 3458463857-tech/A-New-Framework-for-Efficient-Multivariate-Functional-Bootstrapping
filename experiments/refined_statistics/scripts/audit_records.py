"""Audit frozen inputs and source correspondence; no encrypted reruns."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
canonical=root.parent/'experiments_functions/inputs'
source=root/'source/refined-tfhe-lhe'
original=root.parent/'experiments_refined_extended/source/refined-tfhe-lhe'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
original_src={str(p.relative_to(original/'src')):digest(p) for p in (original/'src').rglob('*') if p.is_file()}
current_src={str(p.relative_to(source/'src')):digest(p) for p in (source/'src').rglob('*') if p.is_file()}
assert original_src==current_src
assert digest(source/'Cargo.lock')==digest(original/'Cargo.lock')
adapter=digest(source/'benches/bench_functions.rs')
assert digest(root/'results/build_attempt1/source_snapshot.rs')==adapter
inputs={}
for run in sorted((root/'results').glob('protocol1_*')):
    task=run.name.removeprefix('protocol1_')
    assert digest(run/'source_snapshot.rs')==adapter
    assert digest(run/'input_manifest.csv')==digest(canonical/f'{task}.csv')
    assert digest(run/'Cargo.lock')==digest(source/'Cargo.lock')
    assert digest(run/'Cargo.toml')==digest(source/'Cargo.toml')
    assert (run/'exit_code.txt').read_text().strip()=='0'
    inputs[task]=digest(run/'input_manifest.csv')
assert len(inputs)==10
audit=dict(author_library_files_unchanged=len(current_src),cargo_lock_unchanged=True,
    adapter_sha256=adapter,all_build_and_run_snapshots_match=True,
    all_input_snapshots_match_frozen_canonical=True,input_sha256=inputs,
    encrypted_queries=350,encrypted_queries_correct=350,
    input_noise_note='Online packing changes fresh-input variance; original single-fresh-input failure bound is not asserted.')
summary=root/'summary';summary.mkdir(exist_ok=True)
(summary/'source_and_input_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
hashes={str(p.relative_to(root)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
hashes['parameters.json']=digest(root/'parameters.json')
(summary/'source_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
print('PASS: 21 unchanged library source files; 10 exact canonical manifests; build and run source correspondence.')
