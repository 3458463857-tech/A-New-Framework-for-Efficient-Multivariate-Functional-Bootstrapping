"""Validate the saved t=8 observations and summarize the 30 measured rows."""
from pathlib import Path
import csv, hashlib, json, statistics
R=Path(__file__).resolve().parents[1]
OUT=R/'results/protocol1_attempt1'
S=R/'summary';S.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=list(csv.DictReader((R/'inputs/division_t8.csv').open(newline='',encoding='utf-8')))
allrows=[];results=[]
params={
 'ours':{'library':'tfhe-rs 0.8.7','parameter':'PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS','logical_t':8,'implementation_t':16,'M':22,'n':891,'N':2048,'k':1,'pbs_base_log':21,'pbs_level':1,'ks_base_log':4,'ks_level':4,'message_modulus':4,'carry_modulus':4,'max_noise_level':5},
 'native':{'library':'tfhe-rs 0.8.7','parameter':'PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS','logical_t':8,'radix_blocks':2,'physical_input_bits':4,'n':891,'N':2048,'k':1,'pbs_base_log':21,'pbs_level':1,'ks_base_log':4,'ks_level':4,'message_modulus':4,'carry_modulus':4,'max_noise_level':5},
 'refined':{'parameter':'INT_LHE_BASE_16','logical_t':8,'physical_input_bits':4,'LUT_entries':256,'n':769,'N':2048,'k':1,'pbs_base_log':15,'pbs_level':2,'ks_base_log':4,'ks_level':3,'auto_base_log':7,'auto_level':7,'ss_base_log':17,'ss_level':2,'cbs_base_log':4,'cbs_level':4,'extract_size':2,'input_delta':'2^60','output_delta':'2^59'},
 'meta':{'parameter':'BenchmarkMetaFBS8 / ParamsMetaTemplate','logical_t':8,'precision':8,'positive_half_entries':128,'logical_joint_domain':64,'weights':[1,8],'variance_factor':65,'full_domain':False,'full_torus':True,'input_scale':'2^56','failure_bound_is_fullpath':False}}
for method in ['ours','native','refined','meta']:
 d=OUT/method;assert (d/'exit_code.txt').read_text().strip()=='0'
 log=d/'run.log';lines=log.read_text().splitlines();rows=[]
 if method=='ours':
  for line in lines:
   if line.startswith('ENCRYPTED_RESULT,'):
    v=dict(x.split('=',1) for x in line.split(',')[1:]);rows.append(v)
 elif method in ['native','refined']:
  header=next(l for l in lines if l.startswith('phase,index,'))
  rows=list(csv.DictReader([header]+[l for l in lines if l.startswith(('warmup,','measured,'))]))
 else:
  for line in lines:
   if line.startswith('TRIAL '):
    v=json.loads(line[6:]);v['m'],v['d']=v['inputs'];rows.append(v)
  params[method]['compiled_parameter_output']=next(l for l in lines if l.startswith('AUTHOR_COMPILED_PARAMS '))
  params[method]['input_noise_model']=json.loads(next(l for l in lines if l.startswith('INPUT_NOISE_MODEL '))[18:])
  params[method]['meta_config']=json.loads(next(l for l in lines if l.startswith('META_CONFIG '))[12:])
 assert len(rows)==35,(method,len(rows))
 normalized=[]
 for row,inp in zip(rows,inputs):
  for k in ['phase','index','m','d']:assert str(row[k])==inp[k],(method,k,row,inp)
  actual=int(row['actual']);expected=int(inp['m'])//int(inp['d'])
  assert actual==expected==int(row['expected'])
  ms=float(row.get('elapsed_ms',row.get('total_ms')))
  norm=dict(method=method,phase=inp['phase'],index=int(inp['index']),t=8,m=int(inp['m']),d=int(inp['d']),expected=expected,actual=actual,elapsed_ms=ms,pbs_count=row.get('pbs_count',''))
  normalized.append(norm);allrows.append(norm)
 times=[r['elapsed_ms'] for r in normalized if r['phase']=='measured'];assert len(times)==30
 snapshot=next(d.glob('source_snapshot.*'))
 r=dict(method=method,t=8,mean_ms=statistics.mean(times),population_sd_ms=statistics.pstdev(times),sample_sd_ms=statistics.stdev(times),min_ms=min(times),max_ms=max(times),median_ms=statistics.median(times),warmups=5,samples=30,correct=35,pbs_counts=sorted({int(v['pbs_count']) for v in normalized if v['pbs_count']!=''}),input_sha256=sha(R/'inputs/division_t8.csv'),source_sha256=sha(snapshot),raw_sha256=sha(log),parameters=params[method],run=str(d.relative_to(R)))
 results.append(r)
(S/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
with (S/'results.csv').open('w',newline='',encoding='utf-8') as f:
 keys=['method','t','mean_ms','population_sd_ms','sample_sd_ms','min_ms','max_ms','median_ms','warmups','samples','correct','source_sha256','input_sha256','raw_sha256']
 w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(results)
with (S/'trials.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
(S/'AUDIT.json').write_text(json.dumps(dict(rows=140,matched_input_rows=140,correct_outputs=140,means_use_measured_only=True,standard_deviation_definitions={'population':'divide by 30','sample':'divide by 29'},input_sha256=sha(R/'inputs/division_t8.csv')),indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:r[k] for k in ['method','mean_ms','correct','pbs_counts']} for r in results],indent=2))
