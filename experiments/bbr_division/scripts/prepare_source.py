"""Copy the frozen BBR source into a new, independent working directory."""
from pathlib import Path
import hashlib, json, shutil

root = Path(__file__).resolve().parents[1]
previous = root.parents[2] / 'DCC_fair_comparison_v5' / 'experiments_bbr'
if (root / 'source').exists():
    raise SystemExit('Refusing existing source tree')
for name in ('source', 'parameters'):
    shutil.copytree(previous / name, root / name,
                    ignore=shutil.ignore_patterns('target', '__pycache__', '*.pyc', '.git'))
records = []
for name in ('source', 'parameters'):
    for file in sorted((root / name).rglob('*')):
        if file.is_file():
            rel = file.relative_to(root).as_posix()
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            assert digest == hashlib.sha256((previous / rel).read_bytes()).hexdigest()
            records.append(dict(path=rel, sha256=digest, bytes=file.stat().st_size))
(root / 'provenance').mkdir(exist_ok=True)
(root / 'provenance' / 'SOURCE_BASELINE.json').write_text(json.dumps(dict(
    source=str(previous), author_commit='088029cb4cd3a6b33ac10e0c78ea193b1835216d',
    files=records, note='Exact frozen source copy; new adapters added separately.'), indent=2)+'\n')
print(f'Copied and hash-verified {len(records)} files')
