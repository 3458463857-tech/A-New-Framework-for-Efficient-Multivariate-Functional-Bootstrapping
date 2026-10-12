"""One fixed-seed run of the author's target-LUT decomposition search.

Sbox.from_file rejects nonpermutations; its Sbox constructor accepts all LUTs.
The public search(s,p,n,gamma,sbox) is used unchanged. Division by zero is
assigned the public totalization 0; only d>0 appears in the measured manifest.
"""
from pathlib import Path
import random, time, json, hashlib
import numpy as np
from decomposer.search import search
from decomposer.utils.utils import Sbox
root=Path(__file__).resolve().parents[1]
out=root/'source/author/decompositions/division_t16'
out.mkdir(exist_ok=False)
random.seed(20261010); np.random.seed(20261010)
lut=[(i%16)//(i//16) if i//16 else 0 for i in range(256)]
(out/'target.sbox').write_text(' '.join(map(str,lut))+'\n')
start=time.perf_counter()
dec=search(16,17,2,gamma=1.05,sbox=Sbox(lut,256))
elapsed=time.perf_counter()-start
dec.write_in_file(17,2,str(out))
checks=[]
for index,expected in enumerate(lut):
    base=dec.base_chain.apply([index%16,index//16])
    d=dec.decompositions[0]
    n_i=len(base); products=[]
    for j in range(dec.t_is[0]):
        left=sum(int(a)*int(b) for a,b in zip(base,d.betas[j*n_i:(j+1)*n_i]))%17
        right=sum(int(a)*int(b) for a,b in zip(base,d.D[j]))%17
        products.append(left*right%17)
    linear=sum(int(a)*int(b) for a,b in zip(base,d.betas[dec.t_is[0]*n_i:]))%17
    encoded=(sum(products)+linear)%17
    actual=d.encoding.decode(encoded)
    assert actual==expected, (index,encoded,actual,expected)
    checks.append(dict(m=index%16,d=index//16,expected=expected,field_output=encoded,actual=actual))
report=dict(seed=20261010,s=16,p=17,n=2,gamma=1.05,lambda_=dec.l,
    t_is=dec.t_is,worst_norm=dec.compute_worst_norm(),seconds=elapsed,
    measured_output_digits=1,logical_pbs_first_output=dec.l+2*dec.t_is[0],
    exhaustive_checked=256,legal_domain=240,encoding=d.encoding.encoding,
    target_sha256=hashlib.sha256((out/'target.sbox').read_bytes()).hexdigest(),
    checks=checks)
(root/'evidence/DIVISION_CERTIFICATE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
