"""Read-only validation of released hashes, data, and source/log correspondence."""
from pathlib import Path
import hashlib, json
root=Path(__file__).resolve().parents[1]
index=json.loads((root/'ARCHIVE_FILE_INDEX.json').read_text())
for item in index['files']:
    p=root/item['path']
    assert p.stat().st_size==item['bytes'],item['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],item['path']
out=root/'results/counts_protocol1'
src=root/'source/author/bench/HLUT-rs/src'
for a,b in [('source_snapshot.rs','bin/matched_tasks.rs'),('decomposition_snapshot.rs','decomposition.rs'),('files_snapshot.rs','files.rs')]:
    assert (out/a).read_bytes()==(src/b).read_bytes(),(a,b)
for row in json.loads((root/'summary.json').read_text()):
    records=[json.loads(line) for line in (root/row['raw']).read_text().splitlines()]
    assert len(records)==35 and sum(r['phase']=='measured' for r in records)==30
    assert all(r['actual']==r['expected'] and r['correct'] for r in records)
    assert hashlib.sha256((root/row['input_manifest']).read_bytes()).hexdigest()==row['input_sha256']
print(f"PASS: {index['file_count']} hashes; 140 correct records; exact measured source snapshots and input manifests")
