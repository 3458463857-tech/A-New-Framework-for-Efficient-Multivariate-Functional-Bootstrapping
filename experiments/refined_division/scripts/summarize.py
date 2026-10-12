"""Validate recorded inputs/results and derive every reported statistic."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

root=Path(__file__).resolve().parents[1]
summary=root/'summary'
summary.mkdir(exist_ok=True)
trials=[]
rows=[]
for t in (32,64):
    run=root/f'results/protocol1_refined_div{t}'
    assert (run/'exit_code.txt').read_text().strip()=='0'
    log=(run/'run.log').read_text()
    assert 'COMPLETE,measured=30,warmups=5,mismatches=0' in log
    lines=log.splitlines()
    start=next(i for i,x in enumerate(lines) if x.startswith('phase,index,t,m,d,'))
    data=list(csv.DictReader([lines[start]]+[x for x in lines[start+1:] if x.startswith(('warmup,','measured,'))]))
    manifest=list(csv.DictReader((root/f'inputs/division_t{t}.csv').open()))
    assert len(data)==len(manifest)==35
    for actual,expected in zip(data,manifest):
        assert all(actual[k]==expected[k] for k in ('phase','index','t','m','d'))
        assert int(actual['actual'])==int(actual['expected'])==int(actual['m'])//int(actual['d'])
    measured=[r for r in data if r['phase']=='measured']
    assert len(measured)==30
    values=[float(r['total_ms']) for r in measured]
    rows.append(dict(method='Refined-LHE author CBS + two 16-to-4 LUTs',t=t,
        warmups=5,samples=30,correct=35,total=35,mean_ms=statistics.mean(values),
        population_sd_ms=statistics.pstdev(values),sample_sd_ms=statistics.stdev(values),median_ms=statistics.median(values),
        min_ms=min(values),max_ms=max(values),
        mean_input_conversion_ms=statistics.mean(float(r['input_conversion_ms']) for r in measured),
        mean_lut_ms=statistics.mean(float(r['lut_ms']) for r in measured),
        input_blocks=4,output_blocks=2,input_block_bits=4,output_block_bits=4,
        physical_lut_bits=16,logical_input_bits=2*(t.bit_length()-1),
        parameter='INT_LHE_BASE_16',input_delta_log2=60,output_delta_log2=59,
        source_record=f'results/protocol1_refined_div{t}/run.log'))
    trials.extend(data)
with (summary/'timings.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (summary/'trials.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
(summary/'timings.json').write_text(json.dumps(rows,indent=2)+'\n')
source=root/'source/refined-tfhe-lhe'
files=[p for p in source.rglob('*') if p.is_file()]
manifest={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
for p in sorted((root/'inputs').glob('*.csv')):
    manifest[str(p.relative_to(root)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
(summary/'source_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
for r in rows:
    print(f"t={r['t']}: mean {r['mean_ms']:.6f} ms; population SD (ddof=0) {r['population_sd_ms']:.6f}; sample SD (ddof=1) {r['sample_sd_ms']:.6f}; 35/35 correct")
