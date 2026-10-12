#!/usr/bin/env python3
"""Check restored source, inputs, local Cargo/Go references without compiling.
Copyright (c) 2026 DCC contributors. MIT licensed; see ../LICENSE.
"""
from pathlib import Path
import argparse,glob,hashlib,json,re,tomllib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('workspace',type=Path)
p.add_argument('--report',type=Path,required=True)
a=p.parse_args();work=a.workspace.resolve()
mapping=json.loads((ROOT/'docs/provenance/file_map.json').read_text())
changes={r['path']:r for r in json.loads((work/'PREPARATION_CHANGES.json').read_text())}
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
checked=0;omitted=0
for row in mapping:
    rel=row['workspace_path']
    if not rel:continue
    path=work/rel
    if not path.exists():
        assert 'results' in Path(rel).parts or 'experiment_records' in Path(rel).parts,rel
        omitted+=1;continue
    expected=changes[rel]['after_sha256'] if rel in changes else row['sha256']
    assert sha(path)==expected,rel;checked+=1
cargo=[];missing=[];go=[];targets=[];members=[]
for manifest in sorted(work.rglob('Cargo.toml')):
    data=tomllib.loads(manifest.read_text())
    def walk(obj,where=''):
        if isinstance(obj,dict):
            for key,value in obj.items():
                if key in ('dependencies','dev-dependencies','build-dependencies','patch') and isinstance(value,dict):
                    for name,spec in value.items():
                        if isinstance(spec,dict) and isinstance(spec.get('path'),str):
                            target=(manifest.parent/spec['path']).resolve()
                            row=dict(manifest=str(manifest.relative_to(work)),dependency=name,target=str(target),exists=(target/'Cargo.toml').is_file())
                            cargo.append(row)
                            if not row['exists']:missing.append(row)
                walk(value,where+'/'+key)
    walk(data)
    for kind in ('lib','bin','bench','example','test'):
        entries=data.get(kind,[])
        if isinstance(entries,dict):entries=[entries]
        for entry in entries:
            if isinstance(entry.get('path'),str):
                target=(manifest.parent/entry['path']).resolve()
                row=dict(manifest=str(manifest.relative_to(work)),kind=kind,target=str(target),exists=target.is_file())
                targets.append(row)
                if not row['exists']:missing.append(row)
    for pattern in data.get('workspace',{}).get('members',[]):
        found=glob.glob(str(manifest.parent/pattern))
        row=dict(manifest=str(manifest.relative_to(work)),member=pattern,exists=bool(found) and all((Path(q)/'Cargo.toml').is_file() for q in found))
        members.append(row)
        if not row['exists']:missing.append(row)
for manifest in sorted(work.rglob('go.mod')):
    text=manifest.read_text()
    for match in re.finditer(r'=>\s+(\.\.?/[^\s]+)',text):
        target=(manifest.parent/match[1]).resolve()
        row=dict(manifest=str(manifest.relative_to(work)),target=str(target),exists=(target/'go.mod').is_file())
        go.append(row)
        if not row['exists']:missing.append(row)
groups=json.loads((ROOT/'scripts/experiment_groups.json').read_text())
assert all((work/g['workspace_path']).is_dir() for g in groups)
new_root=work/'work/DCC_final_polish_v6/new_experiments'
entrypoints=['source/section3/src/bin/algorithm1_t8_audited.rs',
    'source/section3/src/bin/baseline_div_t8.rs',
    'source/refined-tfhe-lhe/benches/bench_targeted_div8.rs',
    'source/META-FBS/cmd/dcct8/main.go',
    'bbr/source/HLUT-rs/src/bin/matched_division_domains.rs']
for path in entrypoints:assert (new_root/path).is_file(),path
report=dict(files_verified=checked,record_files_intentionally_omitted=omitted,
    experiment_groups=len(groups),cargo_manifests=len(list(work.rglob('Cargo.toml'))),
    local_cargo_references=len(cargo),go_manifests=len(list(work.rglob('go.mod'))),
    explicit_cargo_targets=len(targets),workspace_member_references=len(members),new_division_source_entrypoints=len(entrypoints),
    local_go_references=len(go),missing_local_references=missing,
    compatibility_changes=list(changes.values()),
    dependencies='Compiler installations and registry dependencies are prerequisites; see docs/Reproduction_Guide.md. This checker does not download, compile, or execute benchmarks.')
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='compatibility_changes'},indent=2))
if missing:raise SystemExit(1)
