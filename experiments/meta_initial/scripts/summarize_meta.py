"""Verify the fixed protocol corpus against retained logs and summarize all trials.

No cryptography is run. A suite is selected explicitly, never by fastest time.
"""
from pathlib import Path
import argparse,csv,hashlib,json,statistics

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',default='protocol1');a=ap.parse_args()
    names=[a.protocol+'_div16']+[f'{a.protocol}_count{n}_{p}' for n in [12,16] for p in ['threshold','interval']]
    summaries=[];all_trials=[]
    for name in names:
        run=ROOT/'results'/name
        assert (run/'exit_code.txt').read_text().strip()=='0',name
        lines=(run/'run.log').read_text().splitlines()
        cfg=json.loads(next(x[len('META_CONFIG '):] for x in lines if x.startswith('META_CONFIG ')))
        trials=[json.loads(x[len('TRIAL '):]) for x in lines if x.startswith('TRIAL ')]
        with (run/'input_manifest.csv').open(newline='',encoding='utf-8-sig') as f:inputs=list(csv.DictReader(f))
        assert len(trials)==len(inputs)==35,name
        for record,given in zip(trials,inputs):
            assert record['phase']==given['phase'] and record['index']==int(given['index'])
            if cfg['task']=='div':
                assert (record['m'],record['d'])==(int(given['m']),int(given['d']))
                expected=int(given['m'])//int(given['d'])
            else:
                mask=int(given['bitmask']);assert record['bitmask']==mask
                count=mask.bit_count();n=int(given['n'])
                expected=int(count>=n//2) if cfg['predicate']=='threshold' else int(n//3<=count<=2*n//3)
            assert record['expected']==record['actual']==expected and record['correct'],(name,record)
            all_trials.append(dict(run=name,**record))
        measured=[x['elapsed_ms'] for x in trials if x['phase']=='measured']
        assert len(measured)==30
        summary=dict(run=name,task=cfg['task'],size=cfg['size'],predicate=cfg['predicate'],
            parameter_set=cfg['author_parameter'],warmups=5,trials=30,correct=35,
            mean_ms=statistics.mean(measured),population_sd_ms=statistics.pstdev(measured),
            median_ms=statistics.median(measured),min_ms=min(measured),max_ms=max(measured),
            input_sha256=sha(run/'input_manifest.csv'),adapter_sha256=sha(run/'adapter_snapshot.go'),
            complete_failure_bound_established=False,log=str((run/'run.log').relative_to(ROOT)))
        summaries.append(summary)
    out=ROOT/'summary';out.mkdir(exist_ok=True)
    (out/(a.protocol+'_summary.json')).write_text(json.dumps(summaries,indent=2)+'\n')
    for name,data in [(a.protocol+'_timings.csv',summaries),(a.protocol+'_all_trials.csv',all_trials)]:
        with (out/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    for row in summaries:print(f"{row['task']} {row['size']} {row['predicate']}: {row['mean_ms']:.6f} +/- {row['population_sd_ms']:.6f} ms; 35/35 correct")
if __name__=='__main__':main()
