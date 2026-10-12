"""Validate every recorded input/output, retain failed runs, regenerate paper data."""
import csv,hashlib,io,json,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PARAMS={
 'division':{'name':'PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS','tfhe':'0.8.7','lwe_dimension':891,'glwe_dimension':1,'polynomial_size':2048,'lwe_sigma':1.3292631075564801e-6,'glwe_sigma':2.845267479601915e-15,'pbs_base_log':21,'pbs_level':1,'ks_base_log':4,'ks_level':4,'message_modulus':4,'carry_modulus':4,'max_noise_level':5,'log2_p_fail_library_field':-64.442,'grouping_factor':3,'deterministic_execution':False},
 'count':{'name':'PARAM_MESSAGE_2_CARRY_4_KS_PBS','tfhe':'0.8.7','lwe_dimension':977,'glwe_dimension':1,'polynomial_size':8192,'lwe_sigma':3.0144389706858286e-7,'glwe_sigma':2.168404344971009e-19,'pbs_base_log':15,'pbs_level':2,'ks_base_log':3,'ks_level':6,'message_modulus':4,'carry_modulus':16,'max_noise_level':21,'log2_p_fail_library_field':-64.078},
 'refined_div':{'name':'INT_LHE_BASE_16','tfhe':'0.5.4','lwe_dimension':769,'glwe_dimension':1,'polynomial_size':2048,'lwe_sigma':8.763872947670246e-6,'glwe_sigma':9.25119974676756e-16,'pbs_base_log':15,'pbs_level':2,'ks_base_log':4,'ks_level':3,'auto_base_log':7,'auto_level':7,'auto_fft':'Split(35)','ss_base_log':17,'ss_level':2,'cbs_base_log':4,'cbs_level':4,'log_lut_count':2,'extract_size':2,'message_size':4},
 'refined_count':{'name':'BITWISE_CBS_CMUX3','tfhe':'0.5.4','lwe_dimension':636,'glwe_dimension':1,'polynomial_size':2048,'lwe_sigma':9.25119974676756e-5,'glwe_sigma':9.25119974676756e-16,'pbs_base_log':15,'pbs_level':2,'ks_base_log':2,'ks_level':5,'auto_base_log':7,'auto_level':6,'auto_fft':'Split(35)','ss_base_log':17,'ss_level':2,'cbs_base_log':4,'cbs_level':4,'log_lut_count':2,'extract_size':1,'message_size':1}
}
summaries=[];flat=[];failures=[]
for run in sorted((ROOT/'results').iterdir()):
    if not (run/'run_identity.txt').exists():continue
    identity=dict(line.split('=',1) for line in (run/'run_identity.txt').read_text().splitlines())
    if not (run/'exit_code.txt').exists():continue
    status=int((run/'exit_code.txt').read_text())
    log=(run/'run.log').read_text(errors='replace')
    meta={**identity,'run':run.name,'exit_code':status,'source_sha256':SHA(run/'source_snapshot.rs'),
          'input_manifest_sha256':SHA(run/'input_manifest.csv'),'cargo_lock_sha256':SHA(run/'Cargo.lock'),
          'raw_log_sha256':SHA(run/'run.log'),'raw_path':str((run/'run.log').relative_to(ROOT))}
    if status!=0:
        failures.append(meta);continue
    lines=log.splitlines()
    if identity['method']=='dcc':
        rows=[dict(item.split('=',1) for item in line.split(',')[1:]) for line in lines if line.startswith('ENCRYPTED_RESULT,')]
        for row in rows:row['total_ms']=row['elapsed_ms']
        stages=[dict(item.split('=',1) for item in line.split(',')[1:]) for line in lines if line.startswith('ENCRYPTED_STAGES,')]
        for row in rows:
            stage=next((s for s in stages if s['phase']==row['phase'] and s['index']==row['index']),None)
            if stage:row.update({k:v for k,v in stage.items() if k not in ('phase','index')})
        assert any(line.startswith('ENCRYPTED_SUMMARY,PASS') for line in lines),run
    else:
        header=next(line for line in lines if line.startswith('phase,index,'))
        rows=list(csv.DictReader(io.StringIO(header+'\n'+'\n'.join(line for line in lines if line.startswith(('warmup,','measured,'))))))
        assert 'COMPLETE,measured=30,warmups=5,mismatches=0' in lines,run
    inputs=list(csv.DictReader((run/'input_manifest.csv').open(newline='')))
    assert len(rows)==len(inputs)==35,run
    for row,point in zip(rows,inputs):
        assert (row['phase'],int(row['index']))==(point['phase'],int(point['index'])),run
        if 'm' in point:
            assert (int(row['m']),int(row['d']))==(int(point['m']),int(point['d'])),run
            expected=int(point['m'])//int(point['d'])
        else:
            assert int(row['bitmask'])==int(point['bitmask']),run
            expected=int(point[identity['predicate']])
        assert int(row['actual'])==int(row['expected'])==expected,run
    measured=[r for r in rows if r['phase']=='measured'];warmups=[r for r in rows if r['phase']=='warmup']
    assert len(measured)==30 and len(warmups)==5,run
    values=[float(r['total_ms']) for r in measured]
    data={**meta,'status':'success','samples':30,'warmups':5,'mismatches':0,
          'mean_ms':statistics.mean(values),'population_sd_ms':statistics.pstdev(values),
          'median_ms':statistics.median(values),'min_ms':min(values),'max_ms':max(values),
          'parameters':PARAMS[identity['method'] if identity['method'] not in ('dcc','native') else 'division'],
          'rayon_worker_budget':8,'author_crate_features':'default_monothread' if identity['method'].startswith('refined') else None,
          'cpu_affinity':'0-7 (eight logical CPUs)',
          'threads_note':'All threads are restricted to the same eight logical CPUs. Rayon workers=8; TFHE multibit may create additional internal threads within that CPU affinity. No concurrent self-launched heavy benchmarks.',
          'sample_manifest':'inputs/manifest.json','timing_metadata':[line for line in lines if line.startswith(('META,','ALGORITHM1_CONFIG,','PROTOCOL,'))],
          'resources_metadata':[line for line in lines if line.startswith('RESOURCE,')],
          'failure_evidence_note':'Empirical correctness recorded here. Numerical correctness claims require separate FAILURE_ANALYSIS; library parameter fields are not whole-circuit proofs.',
          'trials':rows}
    for metric in ('pbs_count','input_conversion_ms','lut_ms','input_pbs','subtraction_pbs','outer_pbs'):
        if metric in measured[0]:
            v=[float(r[metric]) for r in measured]
            data[metric]={'mean':statistics.mean(v),'population_sd':statistics.pstdev(v),'min':min(v),'max':max(v)}
    resource=(run/'process_resources.txt').read_text()
    match=re.search(r'Maximum resident set size \(kbytes\): (\d+)',resource)
    data['whole_process_peak_rss_KiB']=int(match.group(1)) if match else None
    data['rss_scope']='Whole process including key setup and all trials; not isolated per-query workspace.'
    (run/'summary.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    summaries.append(data)
    flat.append({k:data[k] for k in ('run','method','size','predicate','samples','warmups','mean_ms','population_sd_ms','median_ms','min_ms','max_ms','source_sha256','input_manifest_sha256')})
out=ROOT/'summary';out.mkdir(exist_ok=True)
(out/'all_results.json').write_text(json.dumps({'runs':summaries,'failed_runs':failures},indent=2)+'\n',encoding='utf-8')
if flat:
    with (out/'timings.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=flat[0]);w.writeheader();w.writerows(flat)
(out/'parameters.json').write_text(json.dumps(PARAMS,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'successful_runs':len(summaries),'failed_runs':failures,'timings':flat},indent=2))
