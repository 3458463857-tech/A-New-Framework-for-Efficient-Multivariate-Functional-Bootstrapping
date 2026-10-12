"""Recompute both BBR measurement summaries from retained per-input records."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('runs',type=Path,nargs='+')
args=parser.parse_args()
args.output_dir.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for run in args.runs:
    run=run.resolve()
    raw=[json.loads(s) for s in (run/'raw.jsonl').read_text().splitlines()]
    inputs=list(csv.DictReader((run/'input.csv').open()))
    assert len(raw)==len(inputs)==35
    for row,expected in zip(raw,inputs):
        assert row['phase']==expected['phase'] and row['index']==int(expected['index'])
        assert (row['t'],row['m'],row['d'])==tuple(int(expected[k]) for k in ('t','m','d'))
        assert row['correct'] and row['actual']==row['m']//row['d']==row['expected']
    assert (run/'exit_code.txt').read_text().strip()=='0'
    measured=[r['elapsed_ms'] for r in raw if r['phase']=='measured']
    assert len(measured)==30 and sum(r['phase']=='warmup' for r in raw)==5
    certificate=json.loads((run/'certificate.json').read_text())
    parameters_line=next(s for s in (run/'stdout.log').read_text().splitlines() if s.startswith('PARAMETERS '))
    parameters=json.loads(parameters_line[len('PARAMETERS '):])
    r=dict(method='BBR26 author evaluator, revised PBS decomposition',t=raw[0]['t'],
        mean_ms=statistics.mean(measured),population_sd_ms=statistics.pstdev(measured),
        sample_sd_ms=statistics.stdev(measured),median_ms=statistics.median(measured),
        min_ms=min(measured),max_ms=max(measured),warmup=5,samples=30,correct=35,
        logical_pbs=certificate['logical_pbs'],lambda_=certificate['lambda_'],
        products=certificate['products'],offline_seconds=certificate['offline_seconds'],
        parameters=parameters,original_parameter_row=certificate['selected_author_parameter_row'],
        failure_estimate='Not recalibrated for revised PBS (15,2); original CSV p_error is not applicable.',
        sampling='Shared manifest: 5 warmup, 10 measured boundary, 20 fixed-seed random; see input.csv',
        timing='All online author sums, LUT encoding/accumulator construction, KS/PBS, products, and output assembly; input encryption/key generation and output decryption excluded.',
        parallelism='Sequential author evaluator; affinity CPUs 0-7; RAYON/OMP/OPENBLAS budget 8.',
        run=str(run.relative_to(root)).replace('\\','/'),
        input_sha256=sha(run/'input.csv'),raw_sha256=sha(run/'raw.jsonl'),
        source_sha256=sha(run/'source_snapshot.rs'),decomposition_source_sha256=sha(run/'decomposition_snapshot.rs'),
        files_source_sha256=sha(run/'files_snapshot.rs'),certificate_sha256=sha(run/'certificate.json'))
    results.append(r)
(args.output_dir/'results.json').write_text(json.dumps(results,indent=2)+'\n')
columns=['method','t','mean_ms','population_sd_ms','sample_sd_ms','median_ms','min_ms','max_ms','warmup','samples','correct','logical_pbs','lambda_','offline_seconds','run','input_sha256','raw_sha256','source_sha256']
with (args.output_dir/'results.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(results)
print(json.dumps(results,indent=2))
