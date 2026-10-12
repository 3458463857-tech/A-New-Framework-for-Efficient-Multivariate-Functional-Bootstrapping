"""Exact, dependency-free C/D certificates. No random or annealing search.

Run: python verify_bbr_mode.py
Writes certificates and machine-generated table fragments in this directory.
The v1 inputs are read-only; the reported historical counts are retained.
"""
from pathlib import Path
from itertools import product
from collections import Counter
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1] / 'DCC_revision_2026-10-10_v1'

def dump(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def csvwrite(name, rows):
    with (HERE/name).open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def mode(x):
    counts=Counter(x)
    return min(counts, key=lambda v:(-counts[v],v))

def median(x):
    return sorted(x)[(len(x)-1)//2]

def certify_additive(case_id, n, t, row, target, historical_records, source):
    """Build Q, then independently verify Q(sum p_i) on every input."""
    lo=n*min(row); hi=n*max(row)
    outputs={}; counts=Counter(); histogram_by_sum={}; conflicts=[]
    for x in product(range(t),repeat=n):
        s=sum(row[a] for a in x)
        y=target(x)
        hist=tuple(x.count(a) for a in range(t))
        if s in outputs and outputs[s]!=y: conflicts.append((x,s,y,outputs[s]))
        outputs[s]=y; counts[s]+=1
        histogram_by_sum.setdefault(s,set()).add(hist)
    assert not conflicts, (case_id,conflicts[:2])
    q=[outputs.get(s,0) for s in range(lo,hi+1)]
    checks=[]
    for i,x in enumerate(product(range(t),repeat=n)):
        s=sum(row[a] for a in x)
        actual=q[s-lo]; expected=target(x)
        assert actual==expected,(case_id,x,s,actual,expected)
        checks.append(dict(index=i,input=','.join(map(str,x)),sum=s,expected=expected,actual=actual,pass_check=True))
    c=dict(case_id=case_id,input_domain=f'[{t}]^{n}',arity=n,alphabet_size=t,
        inner_tables=[list(row) for _ in range(n)],sum_min=lo,sum_max=hi,E=hi-lo,K=len(outputs),
        outer_Q=q,outer_Q_offset=lo,unreachable_fill=0,
        reachable_sums=sorted(outputs),inner_records=n*t,outer_dense_records=hi-lo+1,
        logical_records=n*t+hi-lo+1,historical_records=historical_records,
        full_domain_cases=t**n,verified_cases=len(checks),different_output_collisions=0,
        histogram_is_determined=all(len(v)==1 for v in histogram_by_sum.values()),
        construction_source=source,search_performed=False,global_optimality_claim=False)
    return c,checks,counts

def rank_mod(rows,p):
    basis={}
    for original in rows:
        v=[int(a)%p for a in original]
        for j in sorted(basis):
            c=v[j]
            if c: v=[(a-c*b)%p for a,b in zip(v,basis[j])]
        pivot=next((j for j,a in enumerate(v) if a),None)
        if pivot is not None:
            inv=pow(v[pivot],-1,p)
            basis[pivot]=[(a*inv)%p for a in v]
    return len(basis)

def bbr_certificate(case_id,t,n,p,atoms,beta,target,description):
    H=[]; aug=[]; max_residual=0
    for x in product(range(t),repeat=n):
        v=list(x)
        for atom in atoms:
            assert len(atom['alpha'])==len(v)
            s=sum(a*b for a,b in zip(atom['alpha'],v))%p
            v.append(atom['psi'][s])
        y=target(x)
        result=sum(a*b for a,b in zip(beta,v))%p
        assert result==y,(case_id,x,result,y)
        H.append(v); aug.append(v+[y])
    r=rank_mod(H,p); ra=rank_mod(aug,p)
    assert r==ra
    return dict(case_id=case_id,description=description,domain=f'[{t}]^{n}',
        n=n,t=t,p=p,input_embedding=list(range(t)),lambda_value=len(atoms),product_terms_a=0,
        atomic_chain=atoms,D=[],beta_final=beta,
        equation='f(x)=sum_j beta_final[j]*v[j] mod p; v=(x,atomic_chain(x)); a=0',
        H_rows=t**n,H_columns=n+len(atoms),H_rank=r,augmented_rank=ra,
        full_row_rank=(r==t**n),target_in_column_space=True,
        checked_inputs=t**n,failures=0,logical_PBS_count=len(atoms),
        logical_LUT_records=p*len(atoms),runtime_measured=False,
        random_search_performed=False,optimality_claim=False,
        plaintext_no_wrap_reason=f'count ranges from0 to{n}, strictly below p={p}',
        parameter_warning='This is a valid algebraic BBR representation; homomorphic parameters and noise/conversion costs for this p are not benchmarked.')

def main():
    main_mode,checks,support=certify_additive('mode_t3_n6',6,3,[7,0,5],mode,127,
        'reuse of the existing six-input ternary lower-median histogram statistic (7,0,5); newly generated mode Q')
    main_med,_,_=certify_additive('median_t3_n6',6,3,[7,0,5],median,61,'existing histogram statistic')
    main_mode['tie_rule']='smallest symbol among those of maximum frequency'
    differences=[s for s in main_mode['reachable_sums'] if main_mode['outer_Q'][s]!=main_med['outer_Q'][s]]
    assert differences, 'mode Q must not have been copied from median Q'
    main_mode['reachable_positions_differing_from_median_Q']=differences
    dump('MODE_CERTIFICATE.json',main_mode)
    csvwrite('MODE_CERTIFICATE.csv',[dict(s=s,reachable=s in support,multiplicity=support[s],Q_mode=main_mode['outer_Q'][s],Q_median=main_med['outer_Q'][s]) for s in range(43)])
    csvwrite('MODE_ALL_729.csv',checks)
    source=V1/'03_LaTeX_Source/EN/part_04.tex'
    history_path=HERE/'MODE_HISTORY.json'
    saved_history=json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else {}
    history_hash=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else saved_history.get('source_sha256')
    dump('MODE_HISTORY.json',dict(case='mode_t3_n6',historical_reported_records=127,
        historical_status='preserved as originally reported search result; no original p_i certificate for127 recovered here',
        source=str(source.relative_to(V1)),source_sha256=history_hash,
        new_records=61,new_method='reuse of existing histogram statistic; no new search',
        earlier_source_unchanged=True))

    certs=[main_mode,main_med]
    audit=[]
    frequency=[]
    for n,t,old_m,old_d in [(10,2,31,31),(14,2,43,43),(5,3,78,71),(6,3,127,61),(3,4,76,58)]:
        for name,fn,old in [('mode',mode,old_m),('median',median,old_d)]:
            if t==4:
                audit.append(dict(case_id=f'{name}_t{t}_n{n}',family='frequency',historical_records=old,current_records=old,E='',K='',verified_cases=0,status='historical only; original inner/outer certificate not recovered; no new search'))
                frequency.append((n,t,name,old,False))
                continue
            row=[0,1] if t==2 else [7,0,5]
            c,_,_=certify_additive(f'{name}_t{t}_n{n}',n,t,row,fn,old,'explicit binary count statistic' if t==2 else 'reuse of existing ternary histogram statistic (7,0,5)')
            certs.append(c)
            audit.append(dict(case_id=c['case_id'],family='frequency',historical_records=old,current_records=c['logical_records'],E=c['E'],K=c['K'],verified_cases=c['verified_cases'],status='explicit construction; exhaustive pass; no search'))
            frequency.append((n,t,name,c['logical_records'],c['logical_records']!=old))
    for family,items in [
        ('threshold',[(8,2,[1],4,25),(5,3,[1],2,21),(6,3,[0,2],3,25),(6,4,[0,1,2],3,31),(8,3,[1],4,33)]),
        ('hamming_interval',[(5,2,[1],(1,3),16),(6,2,[1],(2,4),19),(8,2,[1],(3,5),25),(10,2,[1],(4,6),31),(12,2,[1],(5,7),37)]),
        ('symbol_interval',[(6,3,[1],(2,4),25),(6,4,[1,3],(2,4),31)])]:
        for n,t,A,condition,old in items:
            fn=(lambda x,A=A,tau=condition:int(sum(a in A for a in x)>=tau)) if family=='threshold' else (lambda x,A=A,ab=condition:int(ab[0]<=sum(a in A for a in x)<=ab[1]))
            row=[int(a in A) for a in range(t)]
            c,_,_=certify_additive(f'{family}_t{t}_n{n}_A'+''.join(map(str,A)),n,t,row,fn,old,'explicit count statistic; no search')
            c['A']=A;c['outer_condition']=condition;certs.append(c)
            audit.append(dict(case_id=c['case_id'],family=family,historical_records=old,current_records=c['logical_records'],E=c['E'],K=c['K'],verified_cases=c['verified_cases'],status='explicit construction; exhaustive pass; no search'))
    dump('CURRENT_CONSTRUCTION_CERTIFICATES.json',certs)
    csvwrite('CURRENT_TABLE_AUDIT.csv',audit)
    for language in ['EN','ZH']:
        lines=['% Generated by verify_bbr_mode.py; only rows, to insert in the frequency table.']
        for n,t in [(10,2),(14,2),(5,3),(6,3),(3,4)]:
            pair=[r for r in frequency if r[0]==n and r[1]==t]
            vals=[r'\rev{'+str(r[3])+'}' if r[4] else str(r[3]) for r in pair]
            # Retain the historical strategy projection, never label it fixed-function optimum.
            hist_model={(10,2):243,(14,2):1065,(5,3):195,(6,3):355,(3,4):95}[(n,t)]
            lines.append(f'{n} & {t} & {t**n} & {vals[0]} & {hist_model} & {vals[1]} & {hist_model}'+r' \\')
        (HERE/f'frequency_rows_{language}.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    # BBR fixed function 1: a count predicate over ten Boolean inputs.
    n=10;p=11
    atoms=[dict(alpha=[1]*n,psi=[int(4<=s<=6) for s in range(p)],meaning='interval predicate of Hamming weight')]
    interval=bbr_certificate('bbr_hamming_interval_n10',2,n,p,atoms,[0]*n+[1],
        lambda x:int(4<=sum(x)<=6),'Hamming-weight interval [4,6]; one atomic function, no products')
    # BBR fixed function 2: unary membership maps then one atomic threshold.
    n=6;t=4;p=7;A=[0,1,2];atoms=[]
    for i in range(n):
        alpha=[0]*(n+i);alpha[i]=1
        atoms.append(dict(alpha=alpha,psi=[int(a in A) for a in range(p)],meaning=f'indicator(x_{i} in A)'))
    atoms.append(dict(alpha=[0]*n+[1]*n,psi=[int(s>=3) for s in range(p)],meaning='count threshold >=3'))
    threshold=bbr_certificate('bbr_symbol_threshold_t4_n6',t,n,p,atoms,[0]*(n+len(atoms)-1)+[1],
        lambda x:int(sum(a in A for a in x)>=3),'symbol-set threshold A={0,1,2}, tau=3; seven atoms, no products')
    dump('BBR_FIXED_FUNCTION_CERTIFICATES.json',[interval,threshold])
    csvwrite('BBR_FIXED_FUNCTION_SUMMARY.csv',[{k:c[k] for k in ['case_id','domain','p','lambda_value','product_terms_a','H_rows','H_columns','H_rank','augmented_rank','full_row_rank','checked_inputs','failures','logical_PBS_count','logical_LUT_records']} for c in [interval,threshold]])
    report=dict(mode_checks=len(checks),mode_E=42,mode_K=main_mode['K'],mode_records=61,
        independent_mode_outer_differs_at=len(differences),table_rows=len(audit),
        table_rows_exhaustively_checked=sum(a['verified_cases']>0 for a in audit),
        corrections=[a for a in audit if a['historical_records']!=a['current_records']],
        bbr_cases=2,bbr_input_checks=interval['checked_inputs']+threshold['checked_inputs'],
        bbr_target_systems_exactly_solved=True,no_random_search=True)
    dump('CD_VERIFICATION_RESULT.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
