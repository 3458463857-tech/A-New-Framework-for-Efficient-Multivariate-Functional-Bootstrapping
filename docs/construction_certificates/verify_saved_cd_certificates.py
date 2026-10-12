"""Read saved C/D certificates and independently check every finite-domain input.

This verifier does not regenerate Q or optimize/search a representation.
Run with Python 3: python verify_saved_cd_certificates.py
"""
from pathlib import Path
from itertools import product
from collections import Counter
import json

HERE = Path(__file__).resolve().parent

def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))

def expected(case,x):
    name=case['case_id']
    if name.startswith('mode_'):
        counts=Counter(x)
        return min(x,key=lambda a:(-counts[a],a))
    if name.startswith('median_'):
        return sorted(x)[(len(x)-1)//2]
    A=set(case['A']); count=sum(a in A for a in x)
    condition=case['outer_condition']
    if name.startswith('threshold_'):
        return int(count>=condition)
    return int(condition[0]<=count<=condition[1])

def check_additive(case):
    n=case['arity']; t=case['alphabet_size']
    inner=case['inner_tables']; q=case['outer_Q']; offset=case['outer_Q_offset']
    assert len(inner)==n and all(len(row)==t for row in inner)
    assert sum(len(row) for row in inner)+len(q)==case['logical_records']
    sums=set(); count=0
    for x in product(range(t),repeat=n):
        s=sum(inner[i][x[i]] for i in range(n)); sums.add(s)
        assert q[s-offset]==expected(case,x),(case['case_id'],x,s)
        count+=1
    assert len(sums)==case['K']
    assert max(sums)-min(sums)==case['E']
    assert len(q)==case['E']+1 and count==case['full_domain_cases']
    return count

def check_bbr(case):
    p=case['p']; n=case['n']; t=case['t']; count=0
    assert case['product_terms_a']==0 and case['D']==[]
    assert case['logical_PBS_count']==len(case['atomic_chain'])
    assert case['logical_LUT_records']==p*len(case['atomic_chain'])
    for x in product(range(t),repeat=n):
        v=list(x)
        for atom in case['atomic_chain']:
            assert len(atom['alpha'])==len(v) and len(atom['psi'])==p
            s=sum(a*b for a,b in zip(atom['alpha'],v))%p
            v.append(atom['psi'][s])
        assert len(case['beta_final'])==len(v)
        actual=sum(a*b for a,b in zip(case['beta_final'],v))%p
        if case['case_id']=='bbr_hamming_interval_n10':
            target=int(4<=sum(x)<=6)
        elif case['case_id']=='bbr_symbol_threshold_t4_n6':
            target=int(sum(a in {0,1,2} for a in x)>=3)
        else:
            raise ValueError(case['case_id'])
        assert actual==target,(case['case_id'],x,actual,target)
        count+=1
    return count

def main():
    mode=read('MODE_CERTIFICATE.json'); assert check_additive(mode)==729
    additive={c['case_id']:c for c in read('CURRENT_CONSTRUCTION_CERTIFICATES.json')}
    counts={k:check_additive(v) for k,v in additive.items()}
    bbr=read('BBR_FIXED_FUNCTION_CERTIFICATES.json')
    bbr_counts={c['case_id']:check_bbr(c) for c in bbr}
    result=dict(mode_inputs_checked=729,mode_records=mode['logical_records'],
        unique_additive_cases=len(counts),additive_input_checks=sum(counts.values()),
        additive_checks=counts,bbr_checks=bbr_counts,
        bbr_input_checks=sum(bbr_counts.values()),all_pass=True,
        note='Verification reads saved tables; no generation, random search, or annealing.')
    (HERE/'CD_SAVED_CERTIFICATE_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
