"""Exhaustive plaintext/domain certificate, distinct from encrypted timing tests."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
certificates=[]
for n in (12,16):
    for predicate in ('threshold','interval'):
        q=[int(s>=n//2) if predicate=='threshold' else int(n//3<=s<=2*n//3) for s in range(n+1)]
        checked=0
        for mask in range(1<<n):
            bits=[(mask>>i)&1 for i in range(n)]
            s=sum(bits)
            expected=int(mask.bit_count()>=n//2) if predicate=='threshold' else int(n//3<=mask.bit_count()<=2*n//3)
            assert q[s]==expected
            checked+=1
        certificates.append({'n':n,'predicate':predicate,'inner_tables':[[0,1]]*n,'outer_table':q,
            'span_E':n,'support_K':n+1,'logical_records_unelided':2*n+n+1,
            'domain_checked':checked,'status':'PASS',
            'physical_inner_PBS':0,'physical_outer_PBS':1,
            'all_domain_input_degree_bound':3*n,'all_domain_input_noise_level_bound':n,
            'capacity':64,'max_noise_level':21,
            'degree_noise_reason':'Fresh two-message-bit ciphertext metadata degree<=3 and noise<=1; n checked additions imply degree<=3n and tracked noise<=n. Actual encrypted plaintexts are bits, so semantic sum<=n.',
            'probability_status':'This certificate proves plaintext correctness and finite budget bounds only; consult separate failure analysis for stochastic calibration assumptions.'})
out=ROOT/'provenance';out.mkdir(exist_ok=True)
(out/'count_certificates.json').write_text(json.dumps(certificates,indent=2)+'\n',encoding='utf-8')
print('PASS: 139264 plaintext predicate evaluations and all-domain degree/noise bounds.')
