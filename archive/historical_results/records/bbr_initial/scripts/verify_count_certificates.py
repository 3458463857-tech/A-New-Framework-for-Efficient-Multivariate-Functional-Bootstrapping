"""Exhaustive fixed-function verification; no homomorphic timings are inferred."""
from pathlib import Path
import json, hashlib, math, csv
root=Path(__file__).resolve().parents[1]
certs=[]
for n in (12,16):
    for kind in ('threshold','interval'):
        predicate=lambda s: int(s>=n//2) if kind=='threshold' else int(n//3<=s<=2*n//3)
        lut=[predicate(s) for s in range(17)]
        for mask in range(1<<n):
            s=mask.bit_count()
            assert lut[s%17]==predicate(s)
        certs.append(dict(task=f'count-{kind}',n=n,p=17,lambda_=1,a=0,
            atom=dict(alpha=[1]*n,psi=lut),beta_final=[0]*n+[1],
            coefficient_l2=math.sqrt(n),selected_nu=5,exhaustive_inputs=1<<n,
            parameter_table='optimizer_cjp_odd-128.csv',lookup_records=17,
            theorem_scope='Fixed target in column span, not arbitrary-LUT full row rank',
            input_sha256=hashlib.sha256((root/f'inputs/count_n{n}.csv').read_bytes()).hexdigest()))
(root/'evidence/COUNT_CERTIFICATES.json').write_text(json.dumps(certs,indent=2)+'\n')
print('PASS: four a=0 certificates, 139264 predicate evaluations')
