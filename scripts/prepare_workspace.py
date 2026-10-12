#!/usr/bin/env python3
"""Prepare a fresh runnable copy without altering released source or records.

Copyright (c) 2026 DCC contributors. MIT licensed; see ../LICENSE.
"""
import argparse, difflib, hashlib, json, os, shlex, shutil
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
GROUPS=json.loads((ROOT/'scripts/experiment_groups.json').read_text())

def confined(base,relative):
    p=PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or any(':' in x for x in p.parts):
        raise ValueError(f'Unsafe relative path: {relative}')
    result=(base/Path(*p.parts)).resolve()
    if not result.is_relative_to(base.resolve()):raise ValueError(relative)
    return result

def plan(include_records):
    files=json.loads((ROOT/'docs/provenance/file_map.json').read_text(encoding='utf-8'))
    selected={};omitted=0
    for r in files:
        target=r['workspace_path']
        if not target:continue
        # Frozen runners have fixed output names. Preserve these outputs in the
        # public artifact, but leave them absent in the fresh execution copy.
        if not include_records and ('results' in PurePosixPath(target).parts or 'experiment_records' in PurePosixPath(target).parts):
            omitted+=1;continue
        source=confined(ROOT,r['path'])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==r['sha256'],r['path']
        if target in selected:
            assert selected[target]['sha256']==r['sha256'],target
        selected[target]=r
    return selected,omitted

def bash_path(path):
    value=path.as_posix()
    if os.name=='nt' and len(value)>2 and value[1]==':':
        return '/mnt/'+value[0].lower()+value[2:]
    return value

def compatibility_adjustments(dest):
    """Only the execution copy is changed; publish all before/after hashes."""
    relative='work/DCC_final_polish_v6/new_experiments/scripts/run_t8.sh'
    path=confined(dest,relative)
    original_bytes=path.read_bytes();before=original_bytes.decode()
    after=before
    old='export GOROOT="$WORK/DCC_revision_v3/experiments_meta/toolchain/go"'
    new='''if [[ -x "$WORK/DCC_revision_v3/experiments_meta/toolchain/go/bin/go" ]]; then
  export GOROOT="$WORK/DCC_revision_v3/experiments_meta/toolchain/go"
else
  export GOROOT="$(go env GOROOT)"
fi'''
    assert old in after;after=after.replace(old,new,1)
    for old in [
      'cp -a "$WORK/DCC_targeted_revision_v2/final_experiments/build/target" "$ROOT/build/target"',
      'cp -a "$WORK/DCC_targeted_revision_v2/baseline_experiments/build/refined" "$ROOT/build/refined"']:
        assert old in after
        source=old.split('"')[1]
        after=after.replace(old,'if [[ -d "'+source+'" ]]; then '+old+'; fi',1)
    path.write_bytes(after.encode())
    patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
              fromfile='published/'+relative,tofile='execution-copy/'+relative))
    (dest/'PREPARATION_PATCH.diff').write_text(patch,encoding='utf-8')
    changes=[dict(path=relative,before_sha256=hashlib.sha256(original_bytes).hexdigest(),
       after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
       reason='Make optional build-cache copies conditional; use installed Go when the unshipped toolchain is absent. No algorithm, parameters, timing or input changes.')]
    (dest/'PREPARATION_CHANGES.json').write_text(json.dumps(changes,indent=2)+'\n')
    return changes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list',action='store_true',help='List available experiment groups and their readable public paths')
    p.add_argument('--output',type=Path,help='New directory for the execution copy; must not exist')
    p.add_argument('--dry-run',action='store_true',help='Check all copied bytes and paths; do not create the output')
    p.add_argument('--include-records',action='store_true',help='Also restore old result directories for archival auditing, not a fresh run')
    a=p.parse_args()
    if a.list:
        for g in GROUPS:print(f"{g['id']:24} {g['path']}\n  {g['description']}")
        return
    if a.output is None:p.error('--output is required unless --list is used')
    dest=a.output.resolve()
    if dest.exists():p.error(f'Refusing existing output directory: {dest}')
    if dest.is_relative_to(ROOT):p.error('Choose an output outside the published artifact')
    chosen,omitted=plan(a.include_records)
    for name in chosen:confined(dest,name)
    # Required cross-experiment input references in the frozen Meta/Refined code.
    required=[
      'work/DCC_targeted_revision_v2/final_experiments/inputs/division_t32.csv',
      'work/DCC_submission_polish_v4/experiments_functions/inputs/hamming_interval10.csv',
      'work/DCC_fair_comparison_v5/experiments_small_functions/inputs/lower_median3_3.csv',
      'work/DCC_fair_comparison_v5/experiments_bbr/source/HLUT-rs/Cargo.toml',
      'work/DCC_fair_comparison_v5/experiments_bbr/source/tfhe-rs-odd/tfhe/Cargo.toml',
      'work/DCC_revision_v3/experiments_meta/source/META-FBS/go.mod',
      'work/DCC_final_polish_v6/new_experiments/inputs/division_t8.csv',
      'work/DCC_final_polish_v6/new_experiments/source/section3/Cargo.toml',
      'work/DCC_final_polish_v6/new_experiments/source/refined-tfhe-lhe/Cargo.toml',
      'work/DCC_final_polish_v6/new_experiments/source/META-FBS/go.mod',
      'work/DCC_final_polish_v6/new_experiments/bbr/source/HLUT-rs/Cargo.toml',
      'work/DCC_final_polish_v6/new_experiments/bbr/source/tfhe-rs-odd/tfhe/Cargo.toml',
    ]
    for name in required:assert name in chosen,f'Missing required dependency: {name}'
    report={'files_to_copy':len(chosen),'bytes_to_copy':sum(r['bytes'] for r in chosen.values()),
            'old_output_files_left_in_artifact':omitted,'dependency_paths_checked':len(required),
            'output':str(dest),'dry_run':a.dry_run}
    if a.dry_run:
        print(json.dumps(report,indent=2));return
    dest.mkdir(parents=True,exist_ok=False)
    for name,r in chosen.items():
        to=confined(dest,name);to.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(confined(ROOT,r['path']),to)
        if to.suffix=='.sh':to.chmod(to.stat().st_mode|0o111)
    env=['# Source this file from Bash in Linux/WSL. This does not run experiments.',
         'export ARTIFACT='+shlex.quote(bash_path(ROOT)),
         'export REPRODUCTION='+shlex.quote(bash_path(dest))]
    for g in GROUPS:
        env.append('export '+g['id'].upper()+'='+shlex.quote(bash_path(dest/g['workspace_path'])))
    env += ['export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8',
            'export RUN_ID="run_$(date -u +%Y%m%dT%H%M%SZ)"']
    (dest/'environment.sh').write_text('\n'.join(env)+'\n',encoding='utf-8')
    changes=compatibility_adjustments(dest)
    report['execution_copy_adjustments']=len(changes)
    (dest/'PREPARATION.json').write_text(json.dumps(report,indent=2)+'\n')
    (dest/'README.md').write_text('Fresh reproduction workspace\n\nSource environment.sh in Linux/WSL, then follow '+str(ROOT/'docs/Reproduction_Guide.md')+'.\nPublished source/records remain unchanged. PREPARATION_CHANGES.json and PREPARATION_PATCH.diff document the execution-copy adjustments for optional caches and the installed Go toolchain.\n')
    print(json.dumps(report,indent=2))
    print('Next: source '+shlex.quote(bash_path(dest/'environment.sh')))

if __name__=='__main__':main()
