#!/usr/bin/env python3
"""Recompute all measured table cells from logs; optionally run frozen parsers.
Copyright (c) 2026 DCC contributors. MIT licensed; see ../LICENSE.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,shutil,statistics,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def read_trials(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines()
    rows=[]
    for line in lines:
        if line.startswith('ENCRYPTED_RESULT,'):
            rows.append(dict(x.split('=',1) for x in line.split(',')[1:]))
        elif line.startswith('TRIAL '):rows.append(json.loads(line[6:]))
        elif line.startswith('{'):
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict) and 'phase' in r:rows.append(r)
    if not rows:
        header=next(line for line in lines if line.startswith('phase,index,'))
        rows=list(csv.DictReader([header]+[s for s in lines if s.startswith(('warmup,','measured,'))]))
    assert len(rows)==35,(path,len(rows))
    assert sum(r['phase']=='warmup' for r in rows)==5,path
    for r in rows:
        assert int(r['actual'])==int(r['expected']),(path,r)
    values=[float(r.get('elapsed_ms',r.get('total_ms'))) for r in rows if r['phase']=='measured']
    assert len(values)==30,path
    return values

def copy(src,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir():shutil.copytree(src,dest)
    else:shutil.copyfile(src,dest)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True,help='New audit directory; must not exist')
    p.add_argument('--run-frozen-parsers',action='store_true',help='Also execute the original new-division statistics scripts in isolated copies')
    a=p.parse_args();out=a.output.resolve()
    if out.exists():p.error('Refusing existing statistics output directory')
    out.mkdir(parents=True)
    table=json.loads((ROOT/'TABLE_INDEX.json').read_text());results=[]
    for cell in table:
        if cell['status']!='measured':continue
        values=read_trials(ROOT/cell['raw_path'])
        mean=statistics.mean(values);population=statistics.pstdev(values);sample=statistics.stdev(values)
        assert math.isclose(mean,float(cell['mean_ms']),rel_tol=1e-11,abs_tol=1e-9),(cell['task_id'],cell['method'],mean,cell['mean_ms'])
        for key,actual in [('population_sd_ms',population),('sample_sd_ms',sample)]:
            if cell[key]!='':assert math.isclose(actual,float(cell[key]),rel_tol=1e-8,abs_tol=1e-8),(cell['task_id'],key,actual,cell[key])
        results.append(dict(task_id=cell['task_id'],method=cell['method'],mean_ms=mean,
            population_sd_ms=population,sample_sd_ms=sample,samples=30,warmups=5,correct=35,
            raw_path=cell['raw_path'],raw_sha256=hashlib.sha256((ROOT/cell['raw_path']).read_bytes()).hexdigest()))
    (out/'REBUILT_TABLE_STATISTICS.json').write_text(json.dumps(results,indent=2)+'\n')
    with (out/'REBUILT_TABLE_STATISTICS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    frozen=[]
    if a.run_frozen_parsers:
        for name,script in [('bbr_division','summarize.py'),('division_t8','summarize_t8.py')]:
            src=ROOT/'experiments'/name;dest=out/'frozen_parsers'/name
            copy(src/'scripts'/script,dest/'scripts'/script)
            if name=='bbr_division':
                run_names=['fhe_t8_attempt1','fhe_t32_attempt1']
                for run in run_names:copy(src/'results'/run,dest/'results'/run)
                command=[sys.executable,str(dest/'scripts'/script),'--output-dir',str(dest/'summary')]+[str(dest/'results'/r) for r in run_names]
            else:
                copy(src/'inputs',dest/'inputs');copy(src/'results/protocol1_attempt1',dest/'results/protocol1_attempt1')
                command=[sys.executable,str(dest/'scripts'/script)]
            proc=subprocess.run(command,capture_output=True,text=True)
            (dest/'parser_stdout.txt').write_text(proc.stdout)
            (dest/'parser_stderr.txt').write_text(proc.stderr)
            assert proc.returncode==0,(name,proc.stderr)
            original=json.loads((src/'summary/results.json').read_text())
            rebuilt=json.loads((dest/'summary/results.json').read_text())
            for old,new in zip(original,rebuilt):
                for key in ['mean_ms','population_sd_ms','sample_sd_ms','correct','input_sha256','raw_sha256','source_sha256']:
                    assert old[key]==new[key],(name,key,old[key],new[key])
            frozen.append(dict(group=name,rows=len(rebuilt),original_script_sha256=hashlib.sha256((src/'scripts'/script).read_bytes()).hexdigest(),exit_code=proc.returncode))
    report=dict(table_cells_recomputed=len(results),timed_observations=len(results)*30,
        correct_observations_including_warmup=len(results)*35,all_published_means_match=True,
        all_reported_sd_conventions_match=True,frozen_parsers=frozen,
        scope='Only statistics on retained records. No build, search or encrypted computation.')
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
