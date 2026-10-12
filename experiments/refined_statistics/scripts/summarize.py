"""Derive statistics only from complete successful shared-manifest runs."""
from pathlib import Path
import csv,statistics,json,hashlib
root=Path(__file__).resolve().parents[1]
tasks=['lower_median3_6','mode3_6','set_interval4_6','set_threshold4_6','hamming_interval10',
       'max3_6','range3_6','iqr3_6','mad3_6','distinct3_6']
rows=[];trials=[]
for task in tasks:
    run=root/f'results/protocol1_{task}'
    assert (run/'exit_code.txt').read_text().strip()=='0',task
    lines=(run/'run.log').read_text().splitlines()
    assert 'COMPLETE,measured=30,warmups=5,mismatches=0' in lines,task
    start=next(i for i,l in enumerate(lines) if l.startswith('phase,index,task_id,inputs,'))
    data=list(csv.DictReader([lines[start]]+[l for l in lines[start+1:] if l.startswith(('warmup,','measured,'))]))
    manifest=list(csv.DictReader((run/'input_manifest.csv').open()))
    assert len(data)==len(manifest)==35
    for a,b in zip(data,manifest):
        assert all(a[k]==b[k] for k in ['phase','index','task_id','inputs','expected'])
        assert a['expected']==a['actual']
    measured=[r for r in data if r['phase']=='measured'];assert len(measured)==30
    values=[float(r['total_ms']) for r in measured]
    rows.append(dict(method='Refined-LHE',task_id=task,warmups=5,samples=30,correct=35,total=35,
        mean_ms=statistics.mean(values),population_sd_ms=statistics.pstdev(values),
        sample_sd_ms=statistics.stdev(values),median_ms=statistics.median(values),
        min_ms=min(values),max_ms=max(values),
        mean_packing_ms=statistics.mean(float(r['packing_ms']) for r in measured),
        mean_input_conversion_ms=statistics.mean(float(r['input_conversion_ms']) for r in measured),
        mean_lut_ms=statistics.mean(float(r['lut_ms']) for r in measured),
        packing_variance_multiplier=10 if task=='hamming_interval10' else 17,
        whole_path_failure_bound='not established for packed input',
        input_manifest_sha256=hashlib.sha256((run/'input_manifest.csv').read_bytes()).hexdigest(),
        source_record=f'results/protocol1_{task}/run.log'))
    trials.extend(data)
out=root/'summary';out.mkdir(exist_ok=True)
for filename,data in [('timings.csv',rows),('trials.csv',trials)]:
    with (out/filename).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
(out/'timings.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(f"{r['task_id']}: {r['mean_ms']:.6f} +/- {r['population_sd_ms']:.6f} ms (ddof=0), 35/35 correct")
