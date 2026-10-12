"""Read-only verification of retained common-task evidence; no cryptography."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/'source/META-FBS'
COMMIT='5df59404858a0dfe5d4a361ff4934a9ffc8c3023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    result={'author_url':'https://github.com/msh086/META-FBS','commit':COMMIT}
    if (UPSTREAM/'.git').exists():
        head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
        assert head==COMMIT
        changed=subprocess.check_output(['git','-C',str(UPSTREAM),'diff','--name-only','HEAD'],text=True).strip()
        assert not changed,changed
        result['tracked_upstream_files_unchanged']=True
        result['git_status']=subprocess.check_output(['git','-C',str(UPSTREAM),'status','--short'],text=True).strip()
    else:
        result['tracked_upstream_files_unchanged']='Git metadata omitted; shipped source manifest verified below'
    adapter=UPSTREAM/'cmd/dccmeta/main.go'
    result['adapter_sha256']=sha(adapter)
    result['go_mod_sha256']=sha(UPSTREAM/'go.mod')
    result['go_sum_sha256']=sha(UPSTREAM/'go.sum')
    suite=json.loads((ROOT/'summary/protocol1_summary.json').read_text())
    runs=[]
    for item in suite:
        run=ROOT/'results'/item['run']
        assert sha(run/'adapter_snapshot.go')==sha(adapter)==item['adapter_sha256']
        assert (run/'upstream_commit.txt').read_text().strip()==COMMIT
        for name in ['go.mod','go.sum']:assert sha(run/name)==sha(UPSTREAM/name)
        corpus=('division_t16.csv' if item['task']=='div' else f"count_n{item['size']}.csv")
        assert sha(run/'input_manifest.csv')==sha(ROOT/'inputs'/corpus)==item['input_sha256']
        lines=(run/'run.log').read_text().splitlines()
        params=next(x for x in lines if x.startswith('AUTHOR_COMPILED_PARAMS '))
        cfg=json.loads(next(x[len('META_CONFIG '):] for x in lines if x.startswith('META_CONFIG ')))
        assert cfg['complete_failure_bound_established'] is False
        runs.append({'run':item['run'],'compiled_parameters':params,'adapter_config':cfg})
    result['runs']=runs
    result['formal_outputs_verified_by_summarizer']=sum(r['correct'] for r in suite)
    files=['README.md','LICENSE','go.mod','go.sum','tfhe/bootstrap.go','tfhe/bootstrap_lut.go','tfhe/params_list.go','tfhe/params.go','tfhe/tfhe_test.go','cmd/dccmeta/main.go']
    result['source_file_sha256']={name:sha(UPSTREAM/name) for name in files}
    archive=ROOT/'toolchain/go1.24.0.linux-amd64.tar.gz'
    if archive.exists():result['downloaded_go_archive_sha256']=sha(archive)
    out=ROOT/'provenance';out.mkdir(exist_ok=True)
    (out/'audit_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    paths=sorted(p for p in UPSTREAM.rglob('*') if p.is_file() and '.git' not in p.relative_to(UPSTREAM).parts)
    manifest={p.relative_to(UPSTREAM).as_posix():sha(p) for p in paths}
    manifest_path=out/'source_manifest.json'
    if manifest_path.exists():
        assert json.loads(manifest_path.read_text())==manifest,'Shipped source manifest differs'
    else:
        assert (UPSTREAM/'.git').exists(),'Creating an initial manifest requires the pinned Git checkout'
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(runs)} formal runs, {result["formal_outputs_verified_by_summarizer"]} outputs; source/input snapshot hashes match.')
if __name__=='__main__':main()
