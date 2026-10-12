"""One fixed-shape author search; run under the supplied 120-second wrapper.

No atom, product, or elimination algorithm is changed. Only the chosen shape,
first output, rank logging, and p-aware parameter-table lookup are adapters.
"""
from pathlib import Path
import argparse, csv, hashlib, inspect, json, math, random, time
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
out = args.output_dir
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
start = time.perf_counter()
settings = dict(n=2, s=16, lambda_=25, a=11, p=17, gamma=1.05,
                seed=20261010, timeout_seconds=120, output_digits=1)
(out/'SETTINGS.json').write_text(json.dumps(settings, indent=2)+'\n')

import numpy as np
import decomposer.decomposition as module
from decomposer.decomposition import MultiDec, TooMuchIterationsException
from decomposer.encoding import Encoding
from decomposer.utils.utils import Sbox, generate_settings

random.seed(settings['seed'])
np.random.seed(settings['seed'])
author_dir = Path(inspect.getfile(module)).parent
source_hashes = {str(p.relative_to(author_dir)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(author_dir.rglob('*')) if p.is_file() and p.suffix in ('.py','.so')}
(out/'AUTHOR_SOURCE.json').write_text(json.dumps(dict(directory=str(author_dir),
    sha256=source_hashes), indent=2)+'\n')
lut = [m//d if d else 0 for d in range(16) for m in range(16)]
(out/'target.sbox').write_text(' '.join(map(str,lut))+'\n')
trace = (out/'rank_trace.jsonl').open('x')
original_solve = module.solve_overdetermined_linear_system
trials = 0
def traced_solve(*a, **kw):
    global trials
    result = original_solve(*a, **kw)
    trials += 1
    matrix = a[0]
    event = dict(trial=trials, seconds=time.perf_counter()-start,
                 rows=matrix.shape[0], columns=matrix.shape[1],
                 rank=int(matrix.shape[0]-result[2]), rank_defect=int(result[2]),
                 accepted=result[0] is not None)
    trace.write(json.dumps(event)+'\n'); trace.flush()
    print('RANK '+json.dumps(event), flush=True)
    return result
module.solve_overdetermined_linear_system = traced_solve

parameter_rows = list(csv.DictReader((root/'parameters/optimizer_cjp_odd-128.csv').open()))
selected = {}
def select_same_prime(p, nu):
    candidates = sorted((r for r in parameter_rows if int(r['p'])==p and int(r['nu'])>=nu),
                        key=lambda r:int(r['nu']))
    if not candidates:
        raise RuntimeError(f'No unchanged author row p={p} covering author norm {nu}')
    selected.update(candidates[0])
    return int(candidates[0]['nu'])
module.select_and_format_parameters = select_same_prime

dec = MultiDec(generate_settings(2,16,25,11,17,1.05), Sbox(lut,256),
               Encoding.canonical_encoding(16,17))
dec.initialize()
while True:
    try:
        dec.create_decomposition_i(0)
        break
    except TooMuchIterationsException:
        print('AUTHOR_RESTART after 50 failed candidates; same fixed shape/seed stream',flush=True)
dec.t_is = dec.t_is[:-1]  # Remove only the unused next-output shape.
assert dec.t_is == [11] and len(dec.decompositions)==1
elapsed = time.perf_counter()-start
d = dec.decompositions[0]
checks = []
r = 27
for index, expected in enumerate(lut):
    base = dec.base_chain.apply([index%16,index//16])
    assert len(base)==r
    products = []
    for j in range(11):
        left=sum(int(x)*int(y) for x,y in zip(base,d.betas[j*r:(j+1)*r]))%17
        right=sum(int(x)*int(y) for x,y in zip(base,d.D[j]))%17
        products.append(left*right%17)
    linear=sum(int(x)*int(y) for x,y in zip(base,d.betas[11*r:]))%17
    field_output=(sum(products)+linear)%17
    actual=d.encoding.decode(field_output)
    assert actual==expected, (index,expected,actual)
    checks.append(dict(m=index%16,d=index//16,expected=expected,
                       field_output=field_output,actual=actual))
norm=float(dec.compute_worst_norm())
select_same_prime(17,norm)
decomp_dir=out/'decomposition'
decomp_dir.mkdir()
dec.write_in_file(17,2,str(decomp_dir))

# These are bookkeeping of actual integer multipliers, not an independence or
# a tail-probability proof. The author's multiplication repeats right 16 times.
product_forms=[]
for j in range(11):
    left=[int(x) for x in d.betas[j*r:(j+1)*r]]
    right=[int(x) for x in d.D[j]]
    plus=[x+y for x,y in zip(left,right)]
    minus_implemented=[x+16*y for x,y in zip(left,right)]
    product_forms.append(dict(j=j,left=left,right=right,
        plus_l2=math.sqrt(sum(x*x for x in plus)),plus_l1=sum(plus),
        minus_literal_l2=math.sqrt(sum(x*x for x in minus_implemented)),
        minus_literal_l1=sum(minus_implemented)))
report=dict(**settings,author_seconds=elapsed,attempted_matrices=trials,
    exhaustive_checked=256,legal_domain=240,zero_divisor_pad_checked=16,
    author_worst_norm=norm,selected_author_parameter_row=selected,
    logical_pbs=47,encoding=d.encoding.encoding,checks=checks,
    product_noise_forms=product_forms,
    final_linear_beta=[int(x) for x in d.betas[11*r:]],
    final_pbs_output_terms=22,
    caveat='Original author L2 selection; no new proof for correlated whole-path noise or final 22-output sum.',
    target_sha256=hashlib.sha256((out/'target.sbox').read_bytes()).hexdigest())
(out/'DIVISION_CERTIFICATE.json').write_text(json.dumps(report,indent=2)+'\n')
print('SUCCESS '+json.dumps({k:v for k,v in report.items() if k not in
      ('checks','product_noise_forms')}),flush=True)
