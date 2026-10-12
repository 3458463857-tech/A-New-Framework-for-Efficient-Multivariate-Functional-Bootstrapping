"""Bounded fixed-shape BBR search on the actual input domain.

Uses the authors' random Chain, face_splitting, finite-field Gaussian solver,
and product-basis construction. The adapter supplies an explicit row domain
instead of assuming every input coordinate has the same cardinality.
Canonical output encodings are retained (no encoding switching).
"""
from pathlib import Path
import argparse, csv, hashlib, inspect, json, math, random, time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--t', type=int, choices=(8, 32), required=True)
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = args.output_dir
out.mkdir(parents=True, exist_ok=False)
start = time.perf_counter()
t = args.t
n, lambd, products = (2, 13, [4]) if t == 8 else (4, 50, [25, 14])
seed = 20261011
config = dict(t=t, p=17, n=n, lambda_=lambd, products=products,
    seed=seed, maximum_candidates_per_output=3,
    timeout_seconds=120 if t == 8 else 180,
    output_radix=8 if t == 8 else 16,
    input_order=['m', 'd'] if t == 8 else ['m_low4','m_high1','d_low4','d_high1'],
    domain_cardinalities=[8,8] if t == 8 else [16,2,16,2],
    output_order=['q'] if t == 8 else ['q%16','q//16'])
(out/'SETTINGS.json').write_text(json.dumps(config, indent=2)+'\n')

import galois
import numpy as np
from decomposer.chain import Chain
from decomposer.encoding import Encoding
from decomposer.gauss import solve_overdetermined_linear_system
from decomposer.utils.utils import face_splitting

author_dir = Path(inspect.getfile(Chain)).parent
(out/'AUTHOR_SOURCE.json').write_text(json.dumps(dict(directory=str(author_dir),
    sha256={str(p.relative_to(author_dir)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(author_dir.rglob('*')) if p.is_file() and p.suffix in ('.py','.so')}), indent=2)+'\n')
random.seed(seed)
np.random.seed(seed)
F = galois.GF(17)
pairs = [(m,d) for d in range(t) for m in range(t)]
inputs = [[m,d] if t == 8 else [m%16,m//16,d%16,d//16] for m,d in pairs]
targets = [m//d if d else 0 for m,d in pairs]
(out/'target.sbox').write_text(' '.join(map(str, targets))+'\n')
(out/'DOMAIN.json').write_text(json.dumps(dict(inputs=inputs, pairs=pairs, target=targets))+'\n')
trace = (out/'rank_trace.jsonl').open('x')

def event(**kwargs):
    kwargs['seconds'] = time.perf_counter()-start
    trace.write(json.dumps(kwargs)+'\n'); trace.flush()
    print(json.dumps(kwargs), flush=True)

# The original algorithm resamples a deficient base before solving. Bound this
# work explicitly; the wrapper also imposes a hard wall-clock timeout.
for base_attempt in range(1,4):
    chain = Chain.generate_one_random(17,n,lambd)
    base = F(np.array([chain.apply(x) for x in inputs]))
    rank = int(np.linalg.matrix_rank(base))
    event(kind='base', attempt=base_attempt, rank=rank, columns=n+lambd)
    if rank == n+lambd:
        break
else:
    raise RuntimeError('Three bounded base-chain samples lacked full column rank')

decs = []
for output_index, a in enumerate(products):
    U = np.concatenate([base]+[d['products'] for d in decs], axis=1)
    r = U.shape[1]
    structural_maximum = r*(a+1)-a*(a-1)//2
    assert structural_maximum >= len(inputs)
    target = F(np.array([q if t == 8 else (q//(16**output_index))%16 for q in targets]))
    encoding = Encoding.canonical_encoding(8 if t == 8 else 16,17)
    for attempt in range(1,4):
        D = F(np.random.randint(0,2,size=(a,r)))
        V = U @ D.T
        if int(np.linalg.matrix_rank(V)) != a:
            event(kind='right_basis_rank_deficient', output=output_index, attempt=attempt)
            continue
        V = np.concatenate([V,np.ones((len(inputs),1),dtype='uint8')],axis=1)
        A = F(face_splitting(U,V)%17)
        beta, actual_encoding, defect = solve_overdetermined_linear_system(
            A,target,F,encoding,use_encoding_switching=False)
        event(kind='solve', output=output_index, attempt=attempt, rows=len(inputs),
            columns=int(A.shape[1]), rank=len(inputs)-int(defect),
            structural_upper_bound=structural_maximum, accepted=beta is not None)
        if beta is not None:
            assert np.array_equal(A@beta,target)
            product_matrix = (U @ beta[:-r].reshape(a,r).T)*(U @ D.T)
            decs.append(dict(D=D,beta=beta,products=product_matrix,encoding=actual_encoding))
            break
    else:
        raise RuntimeError(f'Output {output_index}: no full-rank candidate in three bounded attempts')

# Independent scalar replay of exactly the author's sequential online algorithm.
checks=[]
for x,(m,d),expected in zip(inputs,pairs,targets):
    state = [int(v) for v in chain.apply(x)]
    actual_digits=[]
    for a, dec in zip(products,decs):
        r=len(state)
        beta=[int(v) for v in dec['beta']]
        right=[[int(v) for v in row] for row in dec['D']]
        prod=[]
        for j in range(a):
            left=sum(v*c for v,c in zip(state,beta[j*r:(j+1)*r]))%17
            rhs=sum(v*c for v,c in zip(state,right[j]))%17
            prod.append(left*rhs%17)
        linear=sum(v*c for v,c in zip(state,beta[a*r:]))%17
        actual_digits.append((sum(prod)+linear)%17)
        state.extend(prod)
    actual=actual_digits[0] if t==8 else actual_digits[0]+16*actual_digits[1]
    assert actual == expected, (x,actual,expected)
    checks.append(dict(m=m,d=d,inputs=x,expected=expected,actual=actual,digits=actual_digits))

worst=0.0
forms=[]
for atom in chain:
    worst=max(worst,math.sqrt(sum(int(v)**2 for v in atom.alphas)))
for i,(a,dec) in enumerate(zip(products,decs)):
    r=dec['D'].shape[1]
    b=[int(v) for v in dec['beta']]
    for j in range(a):
        left=b[j*r:(j+1)*r]
        right=[int(v) for v in dec['D'][j]]
        worst=max(worst,math.sqrt(sum(v*v for v in left)),math.sqrt(sum(v*v for v in right)))
        forms.append(dict(output=i,product=j,left=left,right=right,
            plus_l1=sum(x+y for x,y in zip(left,right)),
            literal_minus_l1=sum(x+16*y for x,y in zip(left,right)),
            literal_minus_l2=math.sqrt(sum((x+16*y)**2 for x,y in zip(left,right)))))
rows=list(csv.DictReader((root/'parameters/optimizer_cjp_odd-128.csv').open()))
row=min((r for r in rows if int(r['p'])==17 and int(r['nu'])>=worst),key=lambda r:int(r['nu']))
directory=out/'decomposition'; directory.mkdir()
with (directory/f'new_phis_17_{n}').open('x') as f:
    f.write('Base:\n')
    for i,atom in enumerate(chain[n:]):
        f.write(f'{i}:\n'+' '.join(str(v) for v in atom.alphas)+'\n'+' '.join(str(v) for v in atom.psi)+'\n')
for name,key in [('d','D'),('betas','beta')]:
    (directory/f'{name}_17_{n}').write_text(''.join(' '.join(str(v) for v in dec[key].flatten())+'\n' for dec in decs))
(directory/f'sbox_17_{n}').write_text(' '.join(map(str,targets))+'\n')
(directory/f'parameters_17_{n}').write_text(f'l={lambd}\nt_is={products}\nnu={row["nu"]}\n')
with (directory/f'encodings_17_{n}').open('x') as f:
    for i,dec in enumerate(decs):
        f.write(f'Decomposition {i}\n'); dec['encoding'].write_in_file(f)
report=dict(**config,offline_seconds=time.perf_counter()-start,
    exhaustive_checked=t*t,legal_domain=t*(t-1),zero_divisor_pad_checked=t,
    author_worst_norm=worst,selected_author_parameter_row=row,
    logical_pbs=lambd+2*sum(products),checks=checks,product_noise_forms=forms,
    final_linear_betas=[[int(v) for v in dec['beta'][-dec['D'].shape[1]:]] for dec in decs],
    final_pbs_output_terms=[2*a for a in products],
    failure_calibration='Uncalibrated after PBS decomposition override to (15,2); original CSV p_error does not apply.',
    implementation='Unchanged author online evaluator; explicit mixed-domain row enumeration and fixed-shape bounded search adapter.')
(out/'DIVISION_CERTIFICATE.json').write_text(json.dumps(report,indent=2)+'\n')
print('SUCCESS '+json.dumps({k:v for k,v in report.items() if k not in ('checks','product_noise_forms','final_linear_betas')}),flush=True)
