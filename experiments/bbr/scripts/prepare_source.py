"""Prepare an independent source copy; no compilation or measurement."""
from pathlib import Path
import shutil,hashlib,json
root=Path(__file__).resolve().parents[1]
old=root.parents[1]/'DCC_revision_v3/experiments_bbr/source/author'
def copy_file(a,b):
    b.parent.mkdir(parents=True,exist_ok=True)
    if b.exists():
        assert a.read_bytes()==b.read_bytes(), f'Refusing to replace {b}'
    else: shutil.copy2(a,b)
for name in ['LICENSE','README.md','CITATION.cff']:
    copy_file(old/name,root/'source/author_provenance'/name)
for name in ['optimizer_cjp_odd-128.csv','optimizer_cjp_odd-40.csv']:
    copy_file(old/'parameters'/name,root/'parameters'/name)
crate=root/'source/HLUT-rs'
for name in ['Cargo.toml','Cargo.lock']:
    copy_file(old/'bench/HLUT-rs'/name,crate/name)
copy_file(old/'bench/HLUT-rs/src/files.rs',crate/'src/files.rs')
source=(old/'bench/HLUT-rs/src/decomposition.rs').read_text(encoding='utf-8')
source+='''
// Explicit, independently verified fixed-target atoms. The evaluator is unchanged.
impl Decomposition {
    pub fn from_explicit_atoms(n:usize,p:u64,atoms:Vec<(Vec<u64>,Vec<u64>)>,
        beta:Vec<u64>,parameters:BooleanParameters)->Self {
        let l=atoms.len(); assert_eq!(beta.len(),n+l);
        let mut phis=HashMap::new();
        for (i,(alpha,lut)) in atoms.into_iter().enumerate() {
            assert_eq!(alpha.len(),n+i);assert_eq!(lut.len(),p as usize);
            assert!(alpha.iter().chain(lut.iter()).all(|x|*x<p));
            phis.insert((-1,i),(alpha,lut));
        }
        Self {log_s:1,s:2,p,n,l,t_is:vec![0],betas:vec![beta],
            gammas:vec![vec![]],phis,sbox:vec![],parameters,
            encodings:vec![Encoding::new_trivial(p)],cost_pbs:0.0}
    }
}
'''
dest=crate/'src/decomposition.rs'
if dest.exists(): assert dest.read_text(encoding='utf-8')==source
else: dest.write_text(source,encoding='utf-8',newline='\n')
vendor=root/'source/tfhe-rs-odd'
if not vendor.exists():
    shutil.copytree(old/'bench/tfhe-rs-odd',vendor,
        ignore=shutil.ignore_patterns('.git','target','__pycache__','*.pyc'))
files=[crate/'src/files.rs',dest,crate/'src/bin/matched_functions.rs',root/'parameters/optimizer_cjp_odd-128.csv']
report={'author_commit':'088029cb4cd3a6b33ac10e0c78ea193b1835216d',
    'changes':['existing explicit p/nu selection fix','new certificate constructor','new matched-functions harness'],
    'unmodified':'Author homomorphic evaluator and odd-modulus TFHE library',
    'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(root/'evidence/SOURCE_PREPARATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
