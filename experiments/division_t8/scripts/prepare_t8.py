"""Prepare the narrow t=8 extension; never modifies earlier artifacts."""
from pathlib import Path
import csv, json, hashlib, shutil, difflib
R=Path(__file__).resolve().parents[1]
W=R.parents[1]
OLD=W/'DCC_targeted_revision_v2/final_experiments'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for d in ['inputs','source','provenance','results','summary','build']: (R/d).mkdir(exist_ok=True)
mask=(1<<64)-1
state=20261018
def nxt():
 global state
 state=(state+0x9E3779B97F4A7C15)&mask
 z=state; z=((z^(z>>30))*0xBF58476D1CE4E5B9)&mask
 z=((z^(z>>27))*0x94D049BB133111EB)&mask
 return z^(z>>31)
def below(n):
 while True:
  r=nxt()
  if r<(1<<64)-(1<<64)%n: return r%n
t=8
boundary=[(0,t-1),(1,1),(t-1,1),(t-1,t-1),(t//2-2,t-3),(t-2,3),(t//2-1,2),(t//2,3),(t-3,4),(t//2+1,t//2)]
random=[(below(t),1+below(t-1)) for _ in range(20)]
rows=[]
for phase,cases in [('warmup',boundary[:5]),('measured',boundary+random)]:
 for i,(m,d) in enumerate(cases): rows.append(dict(phase=phase,index=i,t=t,m=m,d=d,kind='boundary' if i<10 else 'seeded_random'))
p=R/'inputs/division_t8.csv'
with p.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['phase','index','t','m','d','kind']);w.writeheader();w.writerows(rows)
(R/'inputs/manifest.json').write_text(json.dumps({'seed':20261018,'generator':'SplitMix64 with rejection','warmups':5,'measured':30,'measured_boundary':10,'measured_random':20,'sha256':sha(p),'rows':rows},indent=2)+'\n',encoding='utf-8')
records=[]
def copyrepo(src,dst):
 if not dst.exists(): shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.git','target','build','__pycache__'))
def adapt(src,dst,fn):
 before=src.read_text(encoding='utf-8');after=fn(before)
 dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(after,encoding='utf-8',newline='\n')
 snap=R/'provenance'/('baseline_'+dst.name);shutil.copyfile(src,snap)
 diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(src),tofile=str(dst)))
 (R/'provenance'/(dst.name+'.diff')).write_text(diff,encoding='utf-8')
 records.append({'baseline':str(src),'baseline_sha256':sha(src),'source':str(dst.relative_to(R)),'source_sha256':sha(dst)})
copyrepo(OLD/'source/section3',R/'source/section3')
adapt(OLD/'source/section3/src/bin/algorithm1_t16_audited.rs',R/'source/section3/src/bin/algorithm1_t8_audited.rs',lambda s:s.replace('let selected=read_protocol_manifest(T)?;', 'println!("DOMAIN,logical_t=8,implementation_t=16,reused_t16_circuit=true");\n    let selected=read_protocol_manifest(8)?;'))
adapt(OLD/'source/section3/src/bin/baseline_div_final.rs',R/'source/section3/src/bin/baseline_div_t8.rs',lambda s:s.replace('[16,32,64]','[8]').replace('if t==16','if t<=16').replace('output=t16_one_shortint_otherwise_radix3','output=one_shortint,implementation_bits=4,logical_t=8'))
copyrepo(OLD/'source/refined-tfhe-lhe',R/'source/refined-tfhe-lhe')
adapt(OLD/'source/refined-tfhe-lhe/benches/bench_targeted_div4.rs',R/'source/refined-tfhe-lhe/benches/bench_targeted_div8.rs',lambda s:s.replace('assert_eq!(f[2],"16")','assert_eq!(f[2],"8")').replace('r.2<16 && (1..16)','r.2<8 && (1..8)').replace('seed=20261026','seed=20261018').replace('public_LUT_entries=256','logical_t=8,implementation_input_bits=4,public_LUT_entries=256'))
cargo=R/'source/refined-tfhe-lhe/Cargo.toml'
if 'name = "bench_targeted_div8"' not in cargo.read_text():
 with cargo.open('a',encoding='utf-8') as f:f.write('\n[[bench]]\nname = "bench_targeted_div8"\nharness = false\n')
meta=W/'DCC_fair_comparison_v5/experiments_meta_extended/source/META-FBS'
copyrepo(meta,R/'source/META-FBS')
def metaedit(s):
 s=s.replace('division_t32','division_t8').replace('xs[0] < 32 && xs[1] >= 0 && xs[1] < 32','xs[0] < 8 && xs[1] >= 0 && xs[1] < 8')
 s=s.replace('return target(task, []int{index % 32, index / 32})','if index >= 64 { return 0 }\n\t\treturn target(task, []int{index % 8, index / 8})')
 s=s.replace('integer(row[2]) == 32','integer(row[2]) == 8').replace('precision := 11','precision := 8').replace('weights = []int{1, 32}','weights = []int{1, 8}')
 return s
adapt(meta/'cmd/dccextended/main.go',R/'source/META-FBS/cmd/dcct8/main.go',metaedit)
(R/'provenance/source_changes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'manifest_sha256':sha(p),'rows':len(rows),'source_changes':records},indent=2))
