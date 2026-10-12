"""Verify the frozen shared manifest and summarize an existing BBR t16 run."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('run',type=Path);p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();run=a.run.resolve();out=a.output_dir
if out.exists():raise SystemExit('Refusing existing output directory')
cert=json.loads((run/'certificate.json').read_text())
records=[json.loads(s) for s in (run/'raw.jsonl').read_text().splitlines()]
inputs=list(csv.DictReader((run/'input.csv').open()))
assert len(inputs)==len(records)==35
assert (run/'exit_code.txt').read_text().strip()=='0'
assert cert['exhaustive_checked']==256 and cert['zero_divisor_pad_checked']==16
assert all(c['actual']==(c['m']//c['d'] if c['d'] else 0) for c in cert['checks'])
for x,r in zip(inputs,records):
    assert x['phase']==r['phase'] and int(x['index'])==r['index']
    assert int(x['m'])==r['m'] and int(x['d'])==r['d'] and int(x['t'])==r['t']==16
    assert r['actual']==r['expected']==r['m']//r['d'] and r['correct']
measured=[r['elapsed_ms'] for r in records if r['phase']=='measured']
assert len(measured)==30 and sum(r['phase']=='warmup' for r in records)==5
params=cert['selected_author_parameter_row']
report=dict(task_id='division_t16',method='BBR author evaluator and fixed-shape randomized decomposition',
    mean_ms=statistics.mean(measured),population_sd_ms=statistics.pstdev(measured),
    median_ms=statistics.median(measured),min_ms=min(measured),max_ms=max(measured),
    warmup=5,measured=30,correct_total=35,lambda_=25,a=11,logical_pbs=47,
    source_seed=20261010,search_seconds=cert['author_seconds'],search_candidates=cert['attempted_matrices'],
    matrix_rank=256,verified_plaintext_cases=256,
    parameters=params,input_encoding='individually encrypted m,d in canonical F17; big-LWE key',
    timing='Original partial_lut_evaluation: 25 atom sums/LUTs, 11 two-PBS products, final linear sum; includes accumulator preparation and key switching',
    excluded='key generation, input encryption, output decryption, offline decomposition',
    thread_budget=8,affinity='CPUs 0-7',actual_parallelism='Author products and PBS calls are sequential; Rayon budget eight is retained',
    security_caveat=cert['caveat'],raw_directory=str(run),
    sha256={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in
        ('input.csv','raw.jsonl','source_snapshot.rs','decomposition_snapshot.rs','files_snapshot.rs','certificate.json','parameters.csv','Cargo.lock')})
out.mkdir(parents=True)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
cols=['task_id','mean_ms','population_sd_ms','median_ms','min_ms','max_ms','warmup','measured','correct_total','lambda_','a','logical_pbs']
with (out/'results.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerow({k:report[k] for k in cols})
(out/'RESULTS.md').write_text(f'''# BBR t16 division, fixed-shape author search

The first candidate reached rank 256 and passed all 256 plaintext inputs,
including all 240 legal divisions and 16 zero-divisor padding values.
The shape is lambda=25,a=11; no second shape was searched.

Full encrypted evaluation: **{report['mean_ms']:.6f} ± {report['population_sd_ms']:.6f} ms**
(population standard deviation), median {report['median_ms']:.6f} ms.
Five warmups and thirty measured inputs; 35/35 outputs correct.
The original evaluator performs 47 logical PBS calls, with p=17, nu={params['nu']},
N={params['N']}, small LWE dimension {params['n']}, one PBS decomposition level.

Input values, definitions, timing scope, exact parameters, source and raw-data
hashes are in results.json. Inputs are the same frozen t16 manifest used by R2.
Each operand is separately encrypted; the entire author's homomorphic evaluation
is timed. Offline search and key generation/encryption/decryption are excluded.

This is an actual public-implementation measurement, not a proof of globally
minimum BBR cost. The parameter row is selected using the original author's L2
rule after fixing the prime filter. Literal multipliers in the two PBS product
arguments and the final sum of 22 PBS outputs are explicitly recorded in the
certificate. Neither this calibration nor the zero observed errors establishes
a rigorous full-computation failure-probability bound or a matched security level.
''',encoding='utf-8')
print(json.dumps({k:report[k] for k in cols},indent=2))
