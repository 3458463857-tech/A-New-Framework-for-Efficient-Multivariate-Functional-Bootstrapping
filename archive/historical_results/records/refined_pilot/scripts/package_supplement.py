"""Audit upstream byte identity, preserve provenance, package source and logs only."""
import difflib, hashlib, json, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT.parents[1] / 'DCC_revision_2026-10-10_v1'
OLD = V1 / '05_Reproducibility/third_party/refined-tfhe-lhe'
NEW = ROOT / 'source/refined-tfhe-lhe'
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ref = ROOT/'results/reference_v1'
ref.mkdir(parents=True,exist_ok=True)
old_failure=V1/'05_Reproducibility/results/revision_2026-10-10/baseline_refined'
shutil.copytree(old_failure,ref/'refined_build_failure',dirs_exist_ok=True)
oldlog=V1/'05_Reproducibility/results/revision_2026-10-10/encrypted_final/division16.log'
assert SHA(oldlog)==SHA(ref/'division16.log')
audit=[]
patch=[]
for old in sorted(OLD.rglob('*')):
    if not old.is_file() or any(x in old.parts for x in ('target','build','.git')): continue
    rel=old.relative_to(OLD)
    new=NEW/rel
    if str(rel)=='Cargo.lock':
        continue  # Generated in the previous build attempt, not an upstream source file.
    assert new.exists(),rel
    identical=old.read_bytes()==new.read_bytes()
    if not identical:
        assert str(rel)=='Cargo.toml',f'Unexpected author-source edit: {rel}'
        patch.extend(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix()))
    audit.append({'path':rel.as_posix(),'upstream_sha256':SHA(old),'distributed_sha256':SHA(new),'identical':identical})
adapter=NEW/'benches/bench_targeted_div4.rs'
patch.extend(difflib.unified_diff([],adapter.read_text().splitlines(True),fromfile='/dev/null',tofile='b/benches/bench_targeted_div4.rs'))
provenance=ROOT/'provenance';provenance.mkdir(exist_ok=True)
patchdir=ROOT/'patches';patchdir.mkdir(exist_ok=True)
(patchdir/'adapter.patch').write_text(''.join(patch),encoding='utf-8')
(provenance/'author_source_audit.json').write_text(json.dumps({
    'upstream_url':'https://github.com/KAIST-CryptLab/refined-tfhe-lhe',
    'upstream_commit':'9b0426e8e197020a4bf40776cc03641e6cf9b90e',
    'new_file':'benches/bench_targeted_div4.rs','new_file_sha256':SHA(adapter),
    'changed_upstream_files':['Cargo.toml'],'lockfile':'Generated then frozen; TFHE 0.5.4, rand 0.9.2',
    'reference_log_sha256':SHA(oldlog),'files':audit},indent=2)+'\n',encoding='utf-8')
files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('build','target','.git','__pycache__')) and p.name!='MANIFEST_SHA256.txt']
files.sort(key=lambda p:p.relative_to(ROOT).as_posix())
(ROOT/'MANIFEST_SHA256.txt').write_text(''.join(f'{SHA(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files),encoding='utf-8')
files.append(ROOT/'MANIFEST_SHA256.txt')
out=ROOT.parents[2]/'outputs/refined_lhe_targeted_comparison_source_and_records_2026-10-10_v2.zip'
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files: z.write(p,arcname='refined_lhe_targeted_comparison/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for p in files:
        assert hashlib.sha256(z.read('refined_lhe_targeted_comparison/'+p.relative_to(ROOT).as_posix())).hexdigest()==SHA(p)
print(json.dumps({'path':str(out),'files':len(files),'bytes':out.stat().st_size,'sha256':SHA(out),'unchanged_author_files':sum(r['identical'] for r in audit)},indent=2))
