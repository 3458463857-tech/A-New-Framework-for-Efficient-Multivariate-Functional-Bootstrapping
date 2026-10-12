from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
expected={x['path'] for x in data['files']}
actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in ('MANIFEST.json','MANIFEST_SHA256.txt') and '__pycache__' not in p.parts}
assert actual==expected,(actual-expected,expected-actual)
for item in data['files']:
 p=root/item['path']
 assert p.stat().st_size==item['bytes'],item['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],item['path']
print('PASS:',len(expected),'file hashes; no experiment executed')
