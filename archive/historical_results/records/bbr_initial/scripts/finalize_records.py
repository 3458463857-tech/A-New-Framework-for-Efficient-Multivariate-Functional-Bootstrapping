"""Freeze a file-level release index without including build/runtime artifacts."""
from pathlib import Path
import hashlib, json, re, os
root=Path(__file__).resolve().parents[1]
resources=(root/'results/division_search.resources.txt').read_text()
assert 'Exit status: 124' in resources, 'Only finalize after the bounded search has ended'
stderr=(root/'results/division_search.stderr.log').read_text()
rank_matches=re.findall(r'\[RANK.DECOMP\].*?: (\d+)/\(256, 276\)',stderr)
status=dict(task='division',t=16,status='target decomposition not generated within 300-second search budget',
    homomorphic_runtime_measured=False,exit_status=124,timeout_seconds=300,seed=20261010,
    gamma=1.05,s=16,p=17,n=2,lambda_=21,t0=11,matrix_shape=[256,276],
    completed_rank_reports=len(rank_matches),observed_rank_min=min(map(int,rank_matches)),
    observed_rank_max=max(map(int,rank_matches)),
    structural_rank_bound=221,
    rank_bound_reason='For dim(U)=r<=23 and dim(W)<=s<=11 with W subset U, commutative products span dim(U W)<=r*s-s*(s-1)/2. Adding the linear columns gives rank<=23*11-55+23=221. This is a bound for this selected shape, not an impossibility certificate for the fixed quotient target.',
    input_manifest='inputs/division_t16.csv',
    statement='This finite search outcome does not show inapplicability or an impossibility result. No new search or hand-designed replacement was run.',
    larger_division_tasks='t32 and t64: no target decomposition generated or timed in this bounded follow-up; no cost-model number is substituted.')
(root/'evidence/DIVISION_SEARCH_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
summary=json.loads((root/'summary.json').read_text())
lines=['# Actual BBR26 timings','', '| Task | Mean ± population SD (ms) | Median (ms) | Records |', '|---|---:|---:|---|']
for r in summary:
    lines.append(f"| {r['task']}, n={r['n_or_t']} | {r['mean_ms']:.6f} ± {r['population_sd_ms']:.6f} | {r['median_ms']:.6f} | [{r['raw']}]({r['raw']}) |")
lines+=['', 'All four rows have 5 warmups + 30 measured evaluations, all outputs correct. The parameter table is the author p17/nu5/-128 row; its failure label is not a newly proved whole-circuit bound.', '',
    'The t=16 fixed-seed author target-LUT search reached its 300-second limit with no certificate. No encrypted division time is reported. See [status](evidence/DIVISION_SEARCH_STATUS.json) and [full log](results/division_search.stderr.log). This is a bounded-search outcome, not a claim of inapplicability. No t32/t64 encrypted baseline was run.', '',
    'For the selected shape, r=23 basis columns and s=11 right factors imply a structural rank bound r*s-s*(s-1)/2+r=221, below 256 rows; the 722 completed candidates had ranks 210–221. A fixed target can still lie in this lower-dimensional span, so the rank bound does not establish impossibility for quotient. The author solver returned no target certificate before the timeout.','']
(root/'RESULTS.md').write_text('\n'.join(lines))
skip_parts={'.build','.venv','target','__pycache__','.git','.pytest_cache'}
skip_suffix={'.so','.pyc','.pyo','.pdb','.dll','.exe'}
skip_author_roots={'data','figures','search'}
skip_benches={'bench_cjp','bench_tree_pbs','bench_woppbs'}
files=[]
paths=[]
for directory, subdirs, names in os.walk(root):
    subdirs[:]=[d for d in subdirs if d not in skip_parts]
    for name in names: paths.append(Path(directory)/name)
for path in sorted(paths):
    rel=path.relative_to(root)
    if path.name in {'ARCHIVE_FILE_INDEX.json','MANIFEST_SHA256.txt'}:continue
    if any(p in skip_parts for p in rel.parts) or path.suffix in skip_suffix:continue
    if len(rel.parts)>2 and rel.parts[:2]==('source','author'):
        if rel.parts[2] in skip_author_roots:continue
        if len(rel.parts)>3 and rel.parts[2]=='bench' and rel.parts[3] in skip_benches:continue
    files.append(dict(path=rel.as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
manifest='\n'.join(f"{f['sha256']}  {f['path']}" for f in files)+'\n'
(root/'MANIFEST_SHA256.txt').write_text(manifest)
index=dict(scope='BBR v3 source and all experiment records; no compiled/runtime content',
    excluded_components=sorted(skip_parts|skip_author_roots|skip_benches),excluded_suffixes=sorted(skip_suffix),
    reason='Unrelated author plotting/data and other baseline implementations are omitted; all files needed for the measured HLUT implementation, its patched TFHE dependency, and attempted decomposition generator are included.',
    files=files,total_bytes=sum(f['bytes'] for f in files),file_count=len(files))
(root/'ARCHIVE_FILE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({k:v for k,v in index.items() if k!='files'},indent=2))
