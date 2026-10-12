"""Independently check frozen inputs/outputs and summarize complete runs only."""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, math, statistics

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('run',type=Path)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args(); args.run=args.run.resolve()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('frozen_targets',args.run/'task_definitions.py')
    defs=importlib.util.module_from_spec(spec);spec.loader.exec_module(defs)
    all_rows=[]
    for task_id,(alphabet,n) in defs.TASKS.items():
        case=args.run/task_id
        assert (case/'exit_code.txt').read_text().strip()=='0'
        inputs=list(csv.DictReader((case/'input.csv').open(encoding='utf-8')))
        raw=[json.loads(line) for line in (case/'raw.jsonl').read_text().splitlines()]
        assert len(inputs)==len(raw)==35
        cert=json.loads((case/'certificate.json').read_text())
        for inp,row in zip(inputs,raw):
            xs=list(map(int,inp['inputs'].split(';')))
            expected=defs.target(task_id,xs)
            assert row['inputs']==xs and row['task_id']==task_id
            assert row['phase']==inp['phase'] and row['index']==int(inp['index'])
            assert int(inp['expected'])==row['expected']==row['actual']==expected
            assert row['correct'] and math.isfinite(row['elapsed_ms']) and row['elapsed_ms']>0
        assert sum(r['phase']=='warmup' for r in raw)==5
        times=[r['elapsed_ms'] for r in raw if r['phase']=='measured'];assert len(times)==30
        p_line=next(line for line in (case/'stdout.log').read_text().splitlines() if line.startswith('PARAMETERS '))
        params=json.loads(p_line.split(' ',1)[1])
        assert params==dict(lwe_dimension=849,glwe_dimension=1,polynomial_size=4096,
            lwe_modular_std_dev=1.6512448356449926e-6,glwe_modular_std_dev=2.168404344971009e-19,
            pbs_base_log=25,pbs_level=1,ks_base_log=4,ks_level=4,encryption_key_choice='Big')
        row=dict(task_id=task_id,alphabet=alphabet,n=n,warmups=5,samples=30,correct=35,
            mean_ms=statistics.mean(times),population_sd_ms=statistics.pstdev(times),
            median_ms=statistics.median(times),minimum_ms=min(times),maximum_ms=max(times),
            atoms=len(cert['atoms']),final_linear_terms=sum(cert['output_beta']),
            method='BBR author evaluator + explicit structured certificate',
            field_p=17,author_nu=5,author_local_p_error=2.938735877055719e-39,
            parameter_scope='Original author p17 nu5; no independently proved whole-computation tail bound',
            parameters=params,timing_scope='Complete original author server evaluation; includes packing, encoding/accumulator construction, KS/PBS and final linear selection',
            excluded='Key generation,input encryption,output decryption,offline certificate construction',
            cpu_scope='Same i7-14700; taskset 0-7; Rayon/OMP/OpenBLAS budget 8; sequential CPU PBS evaluator',
            source_sha256=sha(args.run/'source_snapshot.rs'),decomposition_sha256=sha(args.run/'decomposition_snapshot.rs'),
            input_sha256=sha(case/'input.csv'),raw_sha256=sha(case/'raw.jsonl'),
            certificate_sha256=sha(case/'certificate.json'),definitions_sha256=sha(args.run/'task_definitions.py'),
            raw_path=str((case/'raw.jsonl').relative_to(ROOT)).replace('\\','/'))
        all_rows.append(row)
    (args.output_dir/'results.json').write_text(json.dumps(all_rows,indent=2)+'\n',encoding='utf-8')
    flat=[{k:v for k,v in r.items() if k!='parameters'} for r in all_rows]
    with (args.output_dir/'results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lines=['# BBR structured-evaluator measurements','',
        'Five warmups and thirty measured calls per task. SD is population SD. All 350 outputs match the frozen targets.',
        'Explicit certificates are supplied to the original author evaluator; they are not attributed to its random search.','',
        '| Task | Atomic PBS calls | Mean ± population SD (ms) | Median (ms) |',
        '|---|---:|---:|---:|']
    for r in all_rows:lines.append(f"| {r['task_id']} | {r['atoms']} | {r['mean_ms']:.6f} ± {r['population_sd_ms']:.6f} | {r['median_ms']:.6f} |")
    lines+=['','Parameters: original p17/nu5 row; small LWE 849, GLWE k=1, N=4096, PBS 25/1, KS 4/4. The author table labels local failure approximately 2^-128; this is not a newly proved whole-computation failure bound.',
        'Final sums of two or more PBS outputs remain explicitly recorded. Encodings, local failure estimates and attack-security estimates are not normalized across unrelated implementations.','']
    (args.output_dir/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':main()
