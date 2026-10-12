#!/usr/bin/env python3
"""Generate the final release manifest after intentional additions.
Copyright (c) 2026 DCC contributors. MIT licensed; see ../LICENSE.
"""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
excluded={'SHA256SUMS.json','SHA256SUMS.txt'}
rows=[]
for p in sorted(root.rglob('*')):
    if not p.is_file() or (p.parent==root and p.name in excluded):continue
    rows.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,
                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'SHA256SUMS.json').write_text(json.dumps(rows,indent=2)+'\n')
(root/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in rows),encoding='utf-8')
print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows)}))
