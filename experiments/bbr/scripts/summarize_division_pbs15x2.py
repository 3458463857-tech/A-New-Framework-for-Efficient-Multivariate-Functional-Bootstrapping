"""Summarize the retained 5+30 quotient run; never reruns cryptography."""
import csv,hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results/division_fhe_pbs15x2_attempt1'
OUT=ROOT/'summary/division_pbs15x2_attempt1'
assert (RUN/'exit_code.txt').read_text().strip()=='0'
rows=[json.loads(x) for x in (RUN/'raw.jsonl').read_text().splitlines()]
inputs=list(csv.DictReader((RUN/'input.csv').open()))
assert len(rows)==len(inputs)==35
for r,i in zip(rows,inputs):
    assert r['phase']==i['phase'] and r['index']==int(i['index'])
    assert r['m']==int(i['m']) and r['d']==int(i['d'])
    assert r['actual']==r['expected']==r['m']//r['d'] and r['correct']
timed=[r['elapsed_ms'] for r in rows if r['phase']=='measured']
assert len(timed)==30 and len(rows)-len(timed)==5
params=json.loads(next(line[len('PARAMETERS '):] for line in (RUN/'stdout.log').read_text().splitlines() if line.startswith('PARAMETERS ')))
OUT.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'source/HLUT-rs/src/bin/matched_division_pbs15x2.rs'
assert source.read_bytes()==(RUN/'source_snapshot.rs').read_bytes()
summary={
 'task_id':'division_t16','method':'BBR author evaluator, revised PBS decomposition',
 'input_domain':'0<=m<16, 1<=d<16; output floor(m/d)',
 'output_encoding':'one big-LWE, canonical F17 elements 0..15',
 'warmup':5,'timed_samples':30,'correct_all_35':True,
 'mean_ms':statistics.mean(timed),'population_sd_ms':statistics.pstdev(timed),
 'sample_sd_ms':statistics.stdev(timed),'median_ms':statistics.median(timed),
 'min_ms':min(timed),'max_ms':max(timed),
 'logical_pbs':47,'atomic_pbs':25,'multiplication_pbs':22,
 'parameters':params,'author_parameter_row_used_as_base':{'p':17,'nu':55},
 'parameter_override':{'pbs_base_log':15,'pbs_level':2},
 'parameter_qualification':'The original CSV error label is not reassigned to the modified configuration. Whole-path failure probability and concrete security were not re-estimated.',
 'timing_scope':'From two independently encrypted input LWE ciphertexts through all 25 atoms, 11 two-PBS multiplications, linear output combination to one output LWE. Input encryption, key generation, output decryption, offline decomposition and file I/O are outside the timer. No diagnostic decryption inside the production evaluator.',
 'thread_configuration':{'affinity':'CPU 0-7','RAYON_NUM_THREADS':8,'OMP_NUM_THREADS':8,'OPENBLAS_NUM_THREADS':8,'online_author_evaluator':'sequential; no parallel iterator in the timed evaluator'},
 'provenance':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [RUN/'raw.jsonl',RUN/'input.csv',RUN/'source_snapshot.rs',RUN/'decomposition_snapshot.rs',RUN/'files_snapshot.rs',RUN/'Cargo.lock',RUN/'certificate.json']},
 'raw_record':'results/division_fhe_pbs15x2_attempt1/raw.jsonl',
 'diagnosis':'evidence/DIVISION_ROOT_CAUSE_AND_REPAIR.md',
}
(OUT/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
fields=['task_id','method','warmup','timed_samples','mean_ms','population_sd_ms','sample_sd_ms','median_ms','min_ms','max_ms','logical_pbs','correct_all_35']
with (OUT/'results.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerow(summary)
(OUT/'RESULTS.md').write_text(f"# Quotient, revised PBS decomposition\n\n"
 f"The common 5 warm-ups and 30 measured inputs all passed. Mean {summary['mean_ms']:.6f} ms; population SD {summary['population_sd_ms']:.6f} ms; median {summary['median_ms']:.6f} ms.\n\n"
 "This is the original BBR author evaluator with the verified 25-atom / 11-product certificate. Only PBS decomposition changes from (29,1) to (15,2). The online count is still 47 PBS. Neither a client-provided intermediate value nor an extra refresh is used. The earlier failing run is retained.\n\n"
 "The modified parameters do not inherit the original CSV failure label. See results.json for complete timing boundaries, parameters and hashes, and ../../evidence/DIVISION_ROOT_CAUSE_AND_REPAIR.md for the controlled diagnosis.\n")
print(json.dumps(summary,indent=2))
