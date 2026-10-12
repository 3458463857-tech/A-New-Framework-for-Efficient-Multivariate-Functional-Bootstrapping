from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
items=json.loads((root/'MANIFEST_SHA256.json').read_text(encoding='utf-8'))
for item in items:
 p=root/item['path']
 assert p.is_file(),p
 assert p.stat().st_size==item['bytes'],p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
print('Verified',len(items),'payload files')
