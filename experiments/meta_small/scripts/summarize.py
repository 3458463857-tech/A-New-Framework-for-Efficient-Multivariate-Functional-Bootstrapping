"""Audit the frozen seven-task Meta run against the original source and manifests."""
import csv,hashlib,json,statistics
from pathlib import Path
import task_definitions as tasks
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'results/protocol1_attempt1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q95(xs):
    xs=sorted(xs);i=(len(xs)-1)*.95;a=int(i);return xs[a]+(xs[min(a+1,len(xs)-1)]-xs[a])*(i-a)
def tablehash(task):
    n=tasks.TASKS[task][1];out=[]
    for i in range(128):
        if i>=3**n:out.append(0);continue
        xs=[];index=i
        for _ in range(n):xs.append(index%3);index//=3
        out.append(tasks.target(task,xs))
    return hashlib.sha256(bytes(out)).hexdigest()
def main():
    assert (RUN/'finished.txt').exists()
    adapter=ROOT/'source/META-FBS/cmd/dccsmall/main.go'
    assert adapter.read_bytes()==(RUN/'adapter_snapshot.go').read_bytes()==(ROOT/'results/build_attempt1/adapter_snapshot.go').read_bytes()
    original=json.loads((ROOT/'provenance/original_source_manifest.json').read_text())
    for name,digest in original.items():assert sha(ROOT/'source/META-FBS'/name)==digest,name
    manifest=json.loads((ROOT/'inputs/manifest.json').read_text());binding={r['task_id']:r for r in manifest['files']}
    assert sha(ROOT/'scripts/task_definitions.py')==manifest['definitions_sha256']
    rows=[];provenance=[]
    for task,(t,n) in tasks.TASKS.items():
        folder=RUN/task;assert (folder/'exit_code.txt').read_text().strip()=='0'
        lines=(folder/'run.log').read_text().splitlines()
        cfg=json.loads(next(x[len('META_CONFIG '):] for x in lines if x.startswith('META_CONFIG ')))
        model=json.loads(next(x[len('INPUT_NOISE_MODEL '):] for x in lines if x.startswith('INPUT_NOISE_MODEL ')))
        records=[json.loads(x[6:]) for x in lines if x.startswith('TRIAL ')]
        assert len(records)==35 and all(r['correct'] for r in records)
        assert cfg['precision']==8 and cfg['full_domain'] is False and cfg['positive_half_size']==128
        assert cfg['complete_failure_bound_established'] is False
        assert model['variance_factor']==sum(9**i for i in range(n))
        assert model['within_author_capacity'] and model['post_KS_sigma_triangle_bound_plaintext']<=model['allowed_pre_Meta_sigma_plaintext']
        assert cfg['positive_half_table_sha256']==tablehash(task)
        inp=ROOT/'inputs'/(task+'.csv')
        assert inp.read_bytes()==(folder/'input_snapshot.csv').read_bytes()
        assert sha(inp)==cfg['input_sha256']==binding[task]['sha256']
        given=list(csv.DictReader(inp.open()));assert len(given)==35
        for r,g in zip(records,given):
            assert r['task_id']==task and r['phase']==g['phase'] and r['index']==int(g['index']) and r['kind']==g['kind']
            xs=list(map(int,g['inputs'].split(';')));answer=tasks.target(task,xs)
            assert xs==r['inputs'] and answer==r['expected']==r['actual']==int(g['expected'])
        measured=[r['elapsed_ms'] for r in records if r['phase']=='measured'];assert len(measured)==30
        rows.append(dict(task_id=task,parameter='BenchmarkMetaFBS8_positive_half',samples=30,warmups=5,correct=35,mean_ms=statistics.mean(measured),sample_sd_ms=statistics.stdev(measured),median_ms=statistics.median(measured),p95_ms=q95(measured),min_ms=min(measured),max_ms=max(measured),cartesian_inputs_checked=t**n,adapter_sha256=sha(adapter),input_sha256=sha(inp),log_sha256=sha(folder/'run.log'),positive_half_table_sha256=cfg['positive_half_table_sha256']))
        provenance.append(dict(task_id=task,compiled_parameters=next(x for x in lines if x.startswith('AUTHOR_COMPILED_PARAMS ')),configuration=cfg,input_noise_model=model))
    out=ROOT/'summary';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(dict(rows=rows,correct_outputs=245,cartesian_inputs_checked=297,source_input_table_binding='PASS',original_files_unchanged=len(original),statistics='sample SD ddof=1; interpolated p95'),indent=2)+'\n')
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'PASS: 245 outputs, all 297 plaintext inputs and LUT padding; {len(original)} original files unchanged')
    for r in rows:print(f"{r['task_id']},{r['mean_ms']:.6f},{r['sample_sd_ms']:.6f}")
if __name__=='__main__':main()
