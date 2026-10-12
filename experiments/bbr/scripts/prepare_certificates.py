"""Finite, explicitly structured BBR certificates. No encrypted timings.

Uses the frozen ten-task definitions; does not call or impersonate the author's
random full-LUT search. Every candidate and every reachable input is checked.
"""
from pathlib import Path
from itertools import product, combinations
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json

ROOT = Path(__file__).resolve().parents[1]
DEFS = ROOT / 'shared_protocol/scripts/task_definitions.py'
if not DEFS.exists():
    DEFS = ROOT.parents[1] / 'DCC_submission_polish_v4/experiments_functions/scripts/task_definitions.py'
spec = importlib.util.spec_from_file_location('frozen_tasks', DEFS)
tasks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks)
P = 17

def solve_mod(a, b):
    aug = [[v % P for v in row] + [y % P] for row, y in zip(a, b)]
    m, n = len(aug), len(a[0]); r = 0; pivots = []
    for col in range(n):
        pivot = next((j for j in range(r, m) if aug[j][col]), None)
        if pivot is None: continue
        aug[r], aug[pivot] = aug[pivot], aug[r]
        inv = pow(aug[r][col], -1, P)
        aug[r] = [(v * inv) % P for v in aug[r]]
        for j in range(m):
            if j != r and aug[j][col]:
                f = aug[j][col]
                aug[j] = [(u - f*v) % P for u, v in zip(aug[j], aug[r])]
        pivots.append(col); r += 1
        if r == m: break
    consistent = all(any(row[:-1]) or row[-1] == 0 for row in aug[r:])
    if not consistent: return None, r
    ans = [0] * n
    for j, col in enumerate(pivots): ans[col] = aug[j][-1]
    assert all(sum(x*y for x, y in zip(row, ans)) % P == z % P for row, z in zip(a, b))
    return ans, r

def linear_atom(alphabet, arity, function):
    """All nonzero coefficient vectors, modulo multiplication by a nonzero scalar.

    Each checked target depends on every coordinate, so a zero coefficient
    cannot be valid. The first coefficient may therefore be normalized to 1.
    """
    domain = list(product(range(alphabet), repeat=arity)); attempts = 0
    for tail in product(range(1, P), repeat=arity-1):
        alpha = (1,) + tail; values = {}; valid = True; attempts += 1
        for xs in domain:
            key = sum(a*x for a, x in zip(alpha, xs)) % P; y = function(xs)
            if key in values and values[key] != y: valid = False; break
            values[key] = y
        if valid:
            return dict(alpha=list(alpha), lut=[values.get(i, 0) for i in range(P)]), attempts
    return None, attempts

class Certificate:
    def __init__(self, task_id):
        self.task_id = task_id; self.alphabet, self.n = tasks.TASKS[task_id]
        self.atoms = []; self.trace = []
    def atom(self, weights, lut, note):
        alpha = [0] * (self.n + len(self.atoms))
        for index, value in weights.items(): alpha[index] = value
        assert len(lut) == P and all(0 <= x < P for x in lut)
        self.atoms.append(dict(alpha=alpha, lut=lut, note=note))
        return self.n + len(self.atoms)-1
    def output(self, indices):
        self.beta = [0] * (self.n + len(self.atoms))
        for index in indices: self.beta[index] += 1
    def pair_scores(self, score, description):
        indices = []
        for first in range(0, 6, 2):
            lut = [(score(z % self.alphabet) + score(z // self.alphabet)) % P
                   if z < self.alphabet**2 else 0 for z in range(P)]
            indices.append(self.atom({first:1, first+1:self.alphabet}, lut, description))
        return indices
    def evaluate(self, xs):
        values = list(xs)
        for atom in self.atoms:
            values.append(atom['lut'][sum(a*x for a, x in zip(atom['alpha'], values)) % P])
        return sum(a*x for a, x in zip(self.beta, values)) % P
    def export(self):
        checked = 0
        for xs in product(range(self.alphabet), repeat=self.n):
            assert self.evaluate(xs) == tasks.target(self.task_id, list(xs)), (self.task_id, xs)
            checked += 1
        return dict(task_id=self.task_id, alphabet=self.alphabet, n=self.n, p=P,
            author_nu=5, lambda_=len(self.atoms), a=0, atoms=self.atoms,
            output_beta=self.beta, exhaustive_checked=checked, construction=self.trace,
            provenance='explicit structured certificate; not output of author random search',
            noise_scope='Fresh raw-input weighted sums use independence; sums of preceding PBS outputs use absolute coefficient sums; final linear sum is not claimed to have one-PBS error probability.',
            definitions_sha256=hashlib.sha256(DEFS.read_bytes()).hexdigest())

def histogram_certificate(cert):
    hist = [(c0, c1, 6-c0-c1) for c0 in range(7) for c1 in range(7-c0)]
    ys = [tasks.target(cert.task_id, [0]*c0+[1]*c1+[2]*c2) for c0,c1,c2 in hist]
    directions = [(1, 0), (0, 1)] + [(1, k) for k in range(1, P)]
    trials = []
    # A sum of one, two, then three univariate hist-projection functions.
    # This finite family is not claimed to contain globally optimal BBR circuits.
    for size in (1, 2, 3):
        for selected in combinations(directions, size):
            matrix = []
            for c0, c1, _ in hist:
                row = [0] * (P*size)
                for j, (a,b) in enumerate(selected): row[j*P+(a*c0+b*c1)%P] = 1
                matrix.append(row)
            values, rank = solve_mod(matrix, ys)
            trials.append(dict(directions=selected, rank=rank, consistent=values is not None))
            if values is None: continue
            outputs = []
            for j, (a,b) in enumerate(selected):
                # Absorb a,b in the pair LUT: all post-PBS sums have coefficients 1.
                inner = cert.pair_scores(lambda x,a=a,b=b: a if x==0 else b if x==1 else 0,
                    f'pair histogram projection {a}*count0+{b}*count1 modulo 17')
                outputs.append(cert.atom({i:1 for i in inner}, values[j*P:(j+1)*P],
                    'univariate function of the encrypted histogram projection'))
            cert.output(outputs)
            cert.trace.append(dict(method='finite histogram-projection linear solve',
                selected_directions=selected, trials=trials, final_linear_terms=size))
            return
    raise RuntimeError(f'No certificate within the declared three-projection family: {cert.task_id}')

def build(task_id):
    c = Certificate(task_id)
    if task_id == 'hamming_interval10':
        node=c.atom({i:1 for i in range(10)}, [int(4<=s<=6) for s in range(P)], 'count interval')
        c.output([node]); c.trace.append(dict(method='one known count atom'))
    elif task_id.startswith('set_'):
        odd = task_id == 'set_interval4_6'
        inner=c.pair_scores(lambda x:int((x%2==1) if odd else (x%2==0)), 'pair membership count')
        lut=[int(2<=s<=4) if odd else int(s>=3) for s in range(P)]
        c.output([c.atom({i:1 for i in inner},lut,'predicate of the six-symbol membership count')])
        triple, attempts=linear_atom(4,3,lambda xs:sum(int((x%2==1) if odd else x%2==0) for x in xs))
        assert triple is None
        c.trace.append(dict(method='three pair atoms plus one outer',
            rejected_three_input_atom_family='all normalized nonzero F17 coefficients', attempts=attempts))
    elif task_id == 'lower_median3_6':
        zeros=c.pair_scores(lambda x:int(x==0), 'pair count of zero')
        twos=c.pair_scores(lambda x:int(x==2), 'pair count of two')
        left=c.atom({i:1 for i in zeros},[int(s<3) for s in range(P)],'1 - [count0 >= 3]')
        right=c.atom({i:1 for i in twos},[int(s>=4) for s in range(P)],'[count2 >= 4]')
        c.output([left,right]); c.trace.append(dict(method='two count thresholds, linear output',
            final_linear_terms=2, formula='1-[count0>=3]+[count2>=4]'))
    elif task_id == 'max3_6':
        triple, attempts=linear_atom(3,3,max)
        if triple:
            ids=[c.atom({i+j:a for j,a in enumerate(triple['alpha'])},triple['lut'],'three-symbol maximum') for i in [0,3]]
        else:
            lut=[max(z%3,z//3) if z<9 else 0 for z in range(P)]
            ids=[c.atom({i:1,i+1:3},lut,'two-symbol maximum') for i in [0,2,4]]
        while len(ids)>1:
            a,b,*rest=ids
            node=c.atom({a:1,b:3},[max(z%3,z//3) if z<9 else 0 for z in range(P)],'merge maxima')
            ids=[node]+rest
        c.output(ids); c.trace.append(dict(method='maximum reduction',triple_atom_attempts=attempts,
            triple_atom_found=triple is not None))
        histogram = Certificate(task_id)
        histogram_certificate(histogram)
        comparison = dict(maximum_reduction_atoms=len(c.atoms),histogram_atoms=len(histogram.atoms),
            rule='fewer atoms; reduction wins a tie',histogram_trials=histogram.trace)
        if len(histogram.atoms) < len(c.atoms): c = histogram
        c.trace.append(comparison)
    else:
        histogram_certificate(c)
    return c.export()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,default=ROOT/'evidence'/('certificates_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=False)
    result=[]
    for task_id in tasks.TASKS:
        certificate=build(task_id)
        path=args.output_dir/f'{task_id}.json'
        path.write_text(json.dumps(certificate,indent=2)+'\n',encoding='utf-8')
        row={k:certificate[k] for k in ['task_id','lambda_','exhaustive_checked','author_nu']}
        row['certificate_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        result.append(row); print(json.dumps(row),flush=True)
    (args.output_dir/'INDEX.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: all ten fixed-target certificates exhaustively verified')

if __name__ == '__main__': main()
