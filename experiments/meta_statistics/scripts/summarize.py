"""Read-only binding, table, trial and upstream-source audit of the Meta run."""
import csv, hashlib, importlib.util, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parents[1]
DEFS=WORK/'DCC_submission_polish_v4/experiments_functions/scripts/task_definitions.py'
spec=importlib.util.spec_from_file_location('tasks',DEFS);tasks=importlib.util.module_from_spec(spec);spec.loader.exec_module(tasks)
RUN=ROOT/'results/protocol1_attempt1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q95(xs):
    xs=sorted(xs);v=(len(xs)-1)*.95;a=int(v);return xs[a]+(xs[min(a+1,len(xs)-1)]-xs[a])*(v-a)
def expected_table(task,half):
    out=[]
    for index in range(half):
        if task=='division_t32':
            m,d=index%32,index//32;y=0 if d==0 else m//d
        elif task=='hamming_interval10':y=int(4<=index<=6)
        elif index>=729:y=0
        else:
            x=index;xs=[]
            for _ in range(6):xs.append(x%3);x//=3
            y=tasks.target(task,xs)
        out.append(y)
    return hashlib.sha256(bytes(out)).hexdigest()
def main():
    assert (RUN/'finished.txt').exists(),'incomplete run'
    adapter=ROOT/'source/META-FBS/cmd/dccextended/main.go'
    assert adapter.read_bytes()==(RUN/'adapter_snapshot.go').read_bytes()==(ROOT/'results/build_attempt1/adapter_snapshot.go').read_bytes()
    original=WORK/'DCC_revision_v3/experiments_meta'
    source_manifest=json.loads((original/'provenance/source_manifest.json').read_text())
    for name,digest in source_manifest.items():assert sha(ROOT/'source/META-FBS'/name)==digest,(name,'modified original source')
    rows=[];provenance=[]
    ids=['lower_median3_6','mode3_6','max3_6','range3_6','iqr3_6','mad3_6','distinct3_6','hamming_interval10','division_t32']
    for task in ids:
        folder=RUN/task;assert (folder/'exit_code.txt').read_text().strip()=='0'
        lines=(folder/'run.log').read_text().splitlines()
        cfg=json.loads(next(x[12:] for x in lines if x.startswith('META_CONFIG ')))
        model=json.loads(next(x[len('INPUT_NOISE_MODEL '):] for x in lines if x.startswith('INPUT_NOISE_MODEL ')))
        trials=[json.loads(x[6:]) for x in lines if x.startswith('TRIAL ')]
        assert len(trials)==35 and all(x['correct'] for x in trials)
        assert model['within_author_capacity'] and model['post_KS_sigma_triangle_bound_plaintext']<=model['allowed_pre_Meta_sigma_plaintext']
        assert cfg['complete_failure_bound_established'] is False and cfg['full_domain'] is False
        assert cfg['positive_half_table_sha256']==expected_table(task,cfg['positive_half_size'])
        input_path=WORK/'DCC_submission_polish_v4/experiments_functions/inputs'/(task+'.csv')
        if task=='division_t32':input_path=WORK/'DCC_targeted_revision_v2/final_experiments/inputs/division_t32.csv'
        assert input_path.read_bytes()==(folder/'input_snapshot.csv').read_bytes()
        assert sha(input_path)==cfg['input_sha256']
        source_rows=list(csv.DictReader(input_path.open()))
        assert len(source_rows)==35
        for record,given in zip(trials,source_rows):
            assert record['task_id']==task and record['phase']==given['phase'] and record['index']==int(given['index']) and record['kind']==given['kind']
            if task=='division_t32':xs=[int(given['m']),int(given['d'])];expected=xs[0]//xs[1]
            else:xs=list(map(int,given['inputs'].split(';')));expected=tasks.target(task,xs);assert expected==int(given['expected'])
            assert xs==record['inputs'] and expected==record['expected']==record['actual']
        measured=[x['elapsed_ms'] for x in trials if x['phase']=='measured'];assert len(measured)==30
        rows.append(dict(task_id=task,parameter='BenchmarkMetaFBS'+str(cfg['precision'])+'_positive_half',samples=30,warmups=5,correct=35,mean_ms=statistics.mean(measured),sample_sd_ms=statistics.stdev(measured),median_ms=statistics.median(measured),p95_ms=q95(measured),min_ms=min(measured),max_ms=max(measured),adapter_sha256=sha(adapter),input_sha256=sha(input_path),log_sha256=sha(folder/'run.log'),positive_half_table_sha256=cfg['positive_half_table_sha256']))
        provenance.append(dict(task_id=task,compiled_parameters=next(x for x in lines if x.startswith('AUTHOR_COMPILED_PARAMS ')),configuration=cfg,input_noise_model=model))
    out=ROOT/'summary';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(dict(rows=rows,correct_outputs=315,source_input_table_binding='PASS',original_files_unchanged=len(source_manifest),statistics='sample SD ddof=1; linearly interpolated p95'),indent=2)+'\n')
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'PASS: 315 outputs; {len(source_manifest)} original source files unchanged; input/source/table hashes match')
    for r in rows:print(f"{r['task_id']},{r['mean_ms']:.6f},{r['sample_sd_ms']:.6f}")
if __name__=='__main__':main()
