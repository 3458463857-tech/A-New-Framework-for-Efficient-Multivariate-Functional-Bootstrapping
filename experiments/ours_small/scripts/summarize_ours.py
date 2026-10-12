"""Audit frozen source, all 350 trial records, and all 9513 plaintext inputs."""
import csv, hashlib, io, itertools, json, statistics
from pathlib import Path
import large_task_definitions as large
import small_task_definitions as small

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'ours/results/protocol1_attempt1'
TASKS={k:large.TASKS[k] for k in ('hamming_interval10','set_interval4_6','set_threshold4_6')}
TASKS.update(small.TASKS)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q95(xs):
    xs=sorted(xs);i=(len(xs)-1)*.95;a=int(i)
    return xs[a]+(xs[min(a+1,len(xs)-1)]-xs[a])*(i-a)
def main():
    assert (RUN/'finished.txt').exists()
    source=ROOT/'ours/src/bin/functions_checked.rs'
    assert source.read_bytes()==(RUN/'source_snapshot.rs').read_bytes()==(ROOT/'ours/results/build_attempt2/source_snapshot.rs').read_bytes()
    for name in ('Cargo.toml','Cargo.lock'):assert (ROOT/'ours'/name).read_bytes()==(RUN/name).read_bytes()
    rust={r['task_id']:r for r in csv.DictReader((RUN/'plaintext_rust_certificate.csv').open())}
    results=[];certificates=[]
    for task,(t,n) in TASKS.items():
        definition=small if task in small.TASKS else large
        mapping={}
        for xs in itertools.product(range(t),repeat=n):
            score=definition.score(task,xs);answer=definition.target(task,xs)
            assert score not in mapping or mapping[score]==answer
            mapping[score]=answer
        cert=dict(task_id=task,cartesian_inputs=t**n,reachable_scores=len(mapping),maximum_score=max(mapping),output_max=max(mapping.values()))
        for field,value in cert.items():
            if field=='output_max':assert value<=int(rust[task][field]) # Rust records a conservative output bound.
            else:assert str(value)==rust[task][field],(task,field)
        cert['declared_output_bound']=int(rust[task]['output_max'])
        assert rust[task]['check']=='PASS';certificates.append(cert)
        folder=RUN/task;assert (folder/'exit_code.txt').read_text().strip()=='0'
        inp=ROOT/'inputs'/(task+'.csv');assert inp.read_bytes()==(folder/'input_snapshot.csv').read_bytes()
        lines=(folder/'run.log').read_text().splitlines()
        assert lines[-1]==f'COMPLETE,task={task},warmups=5,measured=30,mismatches=0'
        h=lines.index('phase,index,task_id,inputs,expected,actual,pbs_count,total_ms,outer_degree,outer_noise,output_degree,output_noise,kind')
        rows=list(csv.DictReader(io.StringIO('\n'.join(lines[h:-1]))));given=list(csv.DictReader(inp.open()))
        assert len(rows)==len(given)==35
        capacity,noise,pbs,param=(16,15,1,'1_CARRY_3') if t==2 else ((16,5,4,'2_CARRY_2') if t==4 else ((32,10,3,'2_CARRY_3') if n==4 else (16,5,3,'2_CARRY_2')))
        for r,g in zip(rows,given):
            for field in g:assert r[field]==g[field],(task,field)
            expected=definition.target(task,tuple(map(int,r['inputs'].split(';'))))
            assert int(r['expected'])==int(r['actual'])==expected
            assert int(r['pbs_count'])==pbs and int(r['output_noise'])==1
            assert int(r['outer_degree'])<capacity and int(r['outer_noise'])<=noise
            assert int(r['output_degree'])<(2 if t==2 else 4)
        measured=[float(r['total_ms']) for r in rows if r['phase']=='measured'];assert len(measured)==30
        results.append(dict(task_id=task,t=t,n=n,parameter='PARAM_MULTI_BIT_GROUP_3_MESSAGE_'+param+'_KS_PBS_GAUSSIAN_2M64',pbs_count=pbs,samples=30,warmups=5,correct_outputs=35,mean_ms=statistics.mean(measured),sample_sd_ms=statistics.stdev(measured),median_ms=statistics.median(measured),p95_ms=q95(measured),min_ms=min(measured),max_ms=max(measured),cartesian_inputs_checked=t**n,source_sha256=sha(source),input_sha256=sha(inp),log_sha256=sha(folder/'run.log')))
    out=ROOT/'ours/summary';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(dict(rows=results,total_correct_outputs=350,cartesian_inputs_checked=sum(r['cartesian_inputs'] for r in certificates),source_input_binding='PASS',statistics='sample SD ddof=1; p95 interpolated'),indent=2)+'\n')
    (out/'plaintext_certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    print('PASS: 350 encrypted outputs, 9513 plaintext inputs; source/input binding verified')
    for r in results:print(f"{r['task_id']},{r['pbs_count']},{r['mean_ms']:.6f},{r['sample_sd_ms']:.6f}")
if __name__=='__main__':main()
