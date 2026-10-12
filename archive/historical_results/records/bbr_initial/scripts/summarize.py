from pathlib import Path
import json, csv, statistics, hashlib
root=Path(__file__).resolve().parents[1]
out=[]
for path in sorted((root/'results').glob('*_protocol1/*.jsonl')):
    rows=[json.loads(l) for l in path.read_text().splitlines()]
    assert len(rows)==35 and all(r['correct'] for r in rows)
    measured=[r['elapsed_ms'] for r in rows if r['phase']=='measured']
    assert len(measured)==30
    stdout=path.with_suffix('.stdout.log').read_text().splitlines()
    parameters=json.loads(next(l[len('PARAMETERS '):] for l in stdout if l.startswith('PARAMETERS ')))
    selected=json.loads(next(l[len('StringRecord('):-1] for l in stdout if l.startswith('StringRecord(')))
    n=rows[0]['input'].get('n',rows[0]['input'].get('t'))
    input_path=root/'inputs'/f'{"count_n" if rows[0]["task"].startswith("count") else "division_t"}{n}.csv'
    item=dict(implementation='BBR26 author evaluator',task=rows[0]['task'],n_or_t=n,
        warmup=5,measured=30,correct=35,mean_ms=statistics.mean(measured),
        population_sd_ms=statistics.pstdev(measured),median_ms=statistics.median(measured),
        min_ms=min(measured),max_ms=max(measured),raw=str(path.relative_to(root)).replace('\\','/'),
        raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        input_manifest=str(input_path.relative_to(root)).replace('\\','/'),
        input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256((path.parent/'source_snapshot.rs').read_bytes()).hexdigest(),
        field_modulus=int(selected[0]),parameter_nu=int(selected[1]),
        lwe_dimension=parameters['lwe_dimension'],glwe_dimension=parameters['glwe_dimension'],
        polynomial_size=parameters['polynomial_size'],pbs_base_log=parameters['pbs_base_log'],
        pbs_level=parameters['pbs_level'],ks_base_log=parameters['ks_base_log'],ks_level=parameters['ks_level'],
        lwe_sigma=parameters['lwe_modular_std_dev'],glwe_sigma=parameters['glwe_modular_std_dev'],
        author_table_p_error=float(selected[12]),
        parameter_scope='author p17 table (-128), explicit p and nu matching; no new whole-circuit failure proof',
        threads='affinity 0-7; Rayon/OMP/OpenBLAS 8; sequential evaluation kernel',
        timing_scope='all author server evaluation including linear combination and final recovery; excludes keygen/encrypt/decrypt/offline search')
    out.append(item)
(root/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
with (root/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
for r in out: print(r['task'],r['n_or_t'],f"{r['mean_ms']:.9f} +- {r['population_sd_ms']:.9f} ms, median {r['median_ms']:.9f}")
