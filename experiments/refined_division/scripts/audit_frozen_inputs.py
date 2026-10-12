"""One-time provenance check against the earlier frozen experiment, if present."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
old=root.parents[1]/'DCC_targeted_revision_v2/final_experiments'
new=root/'source/refined-tfhe-lhe'
prior=old/'source/refined-tfhe-lhe'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert prior.is_dir(), 'Requires the retained earlier experiment for this provenance check only'
current={str(p.relative_to(new/'src')).replace('\\','/'):digest(p) for p in (new/'src').rglob('*') if p.is_file()}
frozen={str(p.relative_to(prior/'src')).replace('\\','/'):digest(p) for p in (prior/'src').rglob('*') if p.is_file()}
assert current==frozen
assert digest(new/'Cargo.lock')==digest(prior/'Cargo.lock')
inputs={}
for t in (32,64):
    a=root/f'inputs/division_t{t}.csv';b=old/f'inputs/division_t{t}.csv'
    assert digest(a)==digest(b)
    inputs[a.name]=digest(a)
    run=root/f'results/protocol1_refined_div{t}'
    assert digest(run/'source_snapshot.rs')==digest(new/'benches/bench_extended_div.rs')
    assert digest(run/'input_manifest.csv')==digest(a)
audit={'author_library_files_identical_to_frozen_R2':len(current),
       'cargo_lock_identical_to_frozen_R2':True,
       'input_manifests_identical_to_frozen_R2':inputs,
       'both_run_snapshots_match_final_adapter':True,
       'adapter_sha256':digest(new/'benches/bench_extended_div.rs'),
       'full_plaintext_padded_domain_checks_per_run':256*255,
       'empirical_encrypted_queries_passed':70,
       'notes':'No statement that all encrypted inputs were exhaustively evaluated.'}
(root/'summary/frozen_provenance_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
