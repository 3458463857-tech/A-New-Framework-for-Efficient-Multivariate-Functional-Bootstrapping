#!/usr/bin/env python3
"""Verify preserved bytes, table references, and absence of nested archives.
Copyright (c) 2026 DCC contributors. MIT licensed; see ../LICENSE.
"""
from pathlib import Path
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[1]
files=json.loads((ROOT/'docs/provenance/file_map.json').read_text(encoding='utf-8'))
for r in files:
    p=ROOT/r['path']
    assert p.is_file(),r['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
table=json.loads((ROOT/'TABLE_INDEX.json').read_text())
for r in table:
    if r['status']!='measured':continue
    for field in ('summary_path','raw_path','input_path'):
        assert (ROOT/r[field]).is_file(),(r['task_id'],r['method'],field)
    assert hashlib.sha256((ROOT/r['raw_path']).read_bytes()).hexdigest()==r['raw_sha256']
    assert hashlib.sha256((ROOT/r['input_path']).read_bytes()).hexdigest()==r['input_sha256']
    assert hashlib.sha256((ROOT/r['source_snapshot_path']).read_bytes()).hexdigest()==r['source_sha256']
    assert r['samples']==30 and r['warmups']==5
assert not list(ROOT.rglob('*.zip')),'Nested archive found'
for base,dirs,names in os.walk(ROOT):
    # A normal Git clone has a root .git directory, outside released evidence.
    if Path(base)==ROOT and '.git' in dirs:dirs.remove('.git')
    assert not any(name in {'.git','.build','.venv','__pycache__','target'} for name in dirs),'Build/cache directory found'
report={'preserved_source_entries':len(files),'all_original_bytes_verified':True,'table_cells':len(table),
        'measured_cells':sum(r['status']=='measured' for r in table),'all_table_paths_and_input_raw_hashes_verified':True,'nested_archives':0}
manifest=ROOT/'SHA256SUMS.json'
if manifest.exists():
    extra=json.loads(manifest.read_text())
    for r in extra:
        assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
    report['final_manifest_files_verified']=len(extra)
print(json.dumps(report,indent=2))
