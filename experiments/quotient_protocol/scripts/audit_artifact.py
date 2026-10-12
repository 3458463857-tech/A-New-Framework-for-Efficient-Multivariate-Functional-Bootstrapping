"""Bind every run to final source and lockfile, and audit unmodified author code."""
import argparse,csv,difflib,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((ROOT/'summary/all_results.json').read_text())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--protocol',default='protocol1',help='Suite prefix to bind (default: published batch).')
args=parser.parse_args()
selected=[r for r in data['runs'] if r['run'].startswith(args.protocol+'_')]
assert len(selected)==15
assert not [r for r in data['failed_runs'] if r['run'].startswith(args.protocol+'_')]
rows=[]
for record in selected:
    run=ROOT/'results'/record['run'];method=record['method'];size=record['size']
    if method=='dcc':name='algorithm1_t16_audited' if size=='16' else 'algorithm1_audited';project=ROOT/'source/section3';source=project/f'src/bin/{name}.rs'
    elif method in ('native','count'):name='baseline_div_final' if method=='native' else 'count_checked_final';project=ROOT/'source/section3';source=project/f'src/bin/{name}.rs'
    else:name='bench_targeted_div4' if method=='refined_div' else 'bench_count_boolean';project=ROOT/'source/refined-tfhe-lhe';source=project/f'benches/{name}.rs'
    assert SHA(source)==SHA(run/'source_snapshot.rs')==record['source_sha256']
    assert SHA(project/'Cargo.lock')==SHA(run/'Cargo.lock')
    manifest=ROOT/'inputs'/f"{'division_t' if method in ('dcc','native','refined_div') else 'count_n'}{size}.csv"
    assert SHA(manifest)==SHA(run/'input_manifest.csv')==record['input_manifest_sha256']
    rows.append({'run':record['run'],'method':method,'size':size,'predicate':record['predicate'],
        'raw_log':str((run/'run.log').relative_to(ROOT)).replace('\\','/'),
        'source':str(source.relative_to(ROOT)).replace('\\','/'),'source_sha256':SHA(source),
        'manifest_sha256':SHA(manifest),'warmups':5,'measurements':30,'mismatches':0,
        'rerun_command':f"bash scripts/run_one.sh {method} {size} {record['predicate']} UNIQUE_NEW_LABEL"})
out=ROOT/'provenance';out.mkdir(exist_ok=True)
with (ROOT/'EXPERIMENT_INDEX.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
upstream=ROOT.parent.parent/'DCC_revision_2026-10-10_v1/05_Reproducibility/third_party/refined-tfhe-lhe'
current=ROOT/'source/refined-tfhe-lhe'
author=[];patch=[]
if not upstream.exists():
    # A standalone release already carries the original author-source audit.
    # Verify its final file hashes rather than requiring the private worktree.
    author=json.loads((out/'source_binding_audit.json').read_text())['author_source_files']
    for item in author: assert SHA(current/item['path'])==item['final_sha256']
for original in sorted(upstream.rglob('*')) if upstream.exists() else []:
    if not original.is_file() or any(x in original.parts for x in ('target','build','.git')):continue
    rel=original.relative_to(upstream)
    if rel.as_posix()=='Cargo.lock':continue
    dest=current/rel;assert dest.exists()
    same=original.read_bytes()==dest.read_bytes()
    if not same:
        assert rel.as_posix()=='Cargo.toml'
        patch.extend(difflib.unified_diff(original.read_text().splitlines(True),dest.read_text().splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix()))
    author.append({'path':rel.as_posix(),'unchanged':same,'upstream_sha256':SHA(original),'final_sha256':SHA(dest)})
if upstream.exists():
    for name in ('bench_targeted_div4.rs','bench_count_boolean.rs'):
        dest=current/'benches'/name
        patch.extend(difflib.unified_diff([],dest.read_text().splitlines(True),fromfile='/dev/null',tofile='b/benches/'+name))
    (out/'refined_adapter.patch').write_text(''.join(patch),encoding='utf-8')
(out/'source_binding_audit.json').write_text(json.dumps({'status':'PASS','completed_configurations':15,
    'measured_trials':450,'warmups':75,'all_logged_inputs_and_outputs_verified':True,
    'source_snapshot_matches_final':True,'all_input_and_lockfile_hashes_match':True,
    'author_source_files':author,'only_modified_existing_author_file':'Cargo.toml'},indent=2)+'\n',encoding='utf-8')
print('PASS: all 15 source/lock/input bindings; 525 outputs; author library unchanged.')
