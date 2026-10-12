"""Index only portable source, inputs, certificates, and records (no build/cache)."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
skip={'.git','.build','target','.venv','__pycache__','cache','.cache'}
exclude={'ARCHIVE_FILE_INDEX.json','MANIFEST_SHA256.txt'}
items=[]
for p in sorted(root.rglob('*')):
    if not p.is_file(): continue
    rel=p.relative_to(root)
    if any(x in skip for x in rel.parts) or p.suffix in ('.so','.pyc','.pyd'):continue
    if len(rel.parts)==1 and p.name in exclude:continue
    b=p.read_bytes()
    items.append(dict(path=rel.as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(root/'ARCHIVE_FILE_INDEX.json').write_text(json.dumps(dict(
    scope='Portable BBR source, definitions, explicit certificates, all attempts and summaries',
    exclusions=sorted(skip)+['*.so','*.pyc','*.pyd']+sorted(exclude),
    files=items),indent=2)+'\n',encoding='utf-8')
(root/'MANIFEST_SHA256.txt').write_text(''.join(f"{i['sha256']}  {i['path']}\n" for i in items),encoding='utf-8')
for item in items:
    assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256']
print(json.dumps(dict(indexed_files=len(items),bytes=sum(i['bytes'] for i in items))))
