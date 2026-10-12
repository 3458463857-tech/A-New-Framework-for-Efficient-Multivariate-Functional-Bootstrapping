"""Validate frozen inputs/sources/results, then write a distribution manifest.

No compiled objects, caches or virtualenvs are included. No experiment runs.
"""
from pathlib import Path
import ast,hashlib,json

root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((root/'provenance/SOURCE_BASELINE.json').read_text())
for row in baseline['files']:
    assert sha(root/row['path'])==row['sha256'],row['path']
for script in (root/'scripts').glob('*.py'):
    ast.parse(script.read_text())
run_hashes=0
for manifest in (root/'results').rglob('SHA256SUMS'):
    for line in manifest.read_text().splitlines():
        digest,path=line.split(maxsplit=1)
        assert sha(manifest.parent/path)==digest,(manifest,path)
        run_hashes+=1
summary=json.loads((root/'summary/results.json').read_text())
expected_inputs={8:'c634744163c3a8a10cbfacb25593ec0700ca0ea177d9a61798537096582ffe05',
                 32:'740989ffac6e3a0446eb4cd3f8a965888d543b724e802845c971f4e5819b1b6a'}
for row in summary:
    run=root/row['run']
    assert row['input_sha256']==expected_inputs[row['t']]
    assert sha(run/'input.csv')==row['input_sha256']
    assert sha(run/'raw.jsonl')==row['raw_sha256']
    for saved,original,key in [('source_snapshot.rs','bin/matched_division_domains.rs','source_sha256'),
        ('decomposition_snapshot.rs','decomposition.rs','decomposition_source_sha256'),
        ('files_snapshot.rs','files.rs','files_source_sha256')]:
        assert sha(run/saved)==sha(root/'source/HLUT-rs/src'/original)==row[key]
    assert row['correct']==35 and row['samples']==30 and row['warmup']==5
report=dict(original_source_files_unchanged=len(baseline['files']),
    new_configurations=len(summary),correct_outputs=sum(r['correct'] for r in summary),
    per_run_hashes_verified=run_hashes,
    common_input_hashes_pass=True,source_snapshots_match=True,python_syntax='PASS',
    scope='Static distribution verification; no FHE/build/search executed by this checker.')
(root/'evidence/FINAL_CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
excluded={'.build','target','.venv','__pycache__','.git'}
files=[]
for path in sorted(root.rglob('*')):
    rel=path.relative_to(root)
    if path.is_file() and not (set(rel.parts)&excluded) and path.suffix!='.pyc' and path.name not in ('MANIFEST_SHA256.json','MANIFEST_SHA256.txt'):
        files.append(dict(path=rel.as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
(root/'MANIFEST_SHA256.json').write_text(json.dumps(files,indent=2)+'\n')
(root/'MANIFEST_SHA256.txt').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in files))
print(json.dumps(dict(**report,files=len(files),bytes=sum(r['bytes'] for r in files)),indent=2))
