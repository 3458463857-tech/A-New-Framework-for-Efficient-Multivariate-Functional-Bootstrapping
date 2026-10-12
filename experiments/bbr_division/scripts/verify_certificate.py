"""Replay exported BBR files over every input, without the search dependencies."""
from pathlib import Path
import argparse, hashlib, json, re

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('search',type=Path,help='Directory containing DIVISION_CERTIFICATE.json')
args=parser.parse_args()
root=args.search
certificate=json.loads((root/'DIVISION_CERTIFICATE.json').read_text())
t=certificate['t']; n=certificate['n']; p=17
folder=root/'decomposition'
parameter=(folder/f'parameters_17_{n}').read_text()
lambd=int(re.search(r'l=(\d+)',parameter)[1])
products=json.loads(re.search(r't_is=(\[[^\]]+\])',parameter)[1])
lines=(folder/f'new_phis_17_{n}').read_text().splitlines()
assert lines[0]=='Base:'
atoms=[]
for offset in range(1,len(lines),3):
    assert lines[offset]==f'{len(atoms)}:'
    alpha=list(map(int,lines[offset+1].split()))
    lut=list(map(int,lines[offset+2].split()))
    assert len(alpha)==n+len(atoms) and len(lut)==p
    atoms.append((alpha,lut))
assert len(atoms)==lambd
betas=[list(map(int,s.split())) for s in (folder/f'betas_17_{n}').read_text().splitlines()]
gammas=[list(map(int,s.split())) for s in (folder/f'd_17_{n}').read_text().splitlines()]
target=list(map(int,(folder/f'sbox_17_{n}').read_text().split()))
assert len(target)==t*t and len(betas)==len(gammas)==len(products)
checked=0
for d in range(t):
    for m in range(t):
        state=[m,d] if t==8 else [m%16,m//16,d%16,d//16]
        for alpha,lut in atoms:
            state.append(lut[sum(x*y for x,y in zip(alpha,state))%p])
        digits=[]
        for a,beta,gamma in zip(products,betas,gammas):
            r=len(state)
            assert len(beta)==(a+1)*r and len(gamma)==a*r
            prod=[]
            for j in range(a):
                left=sum(x*y for x,y in zip(state,beta[j*r:(j+1)*r]))%p
                right=sum(x*y for x,y in zip(state,gamma[j*r:(j+1)*r]))%p
                # Exactly the two PBS LUT outputs of the author's mult.
                square_plus=(13*(left+right)**2)%p
                square_minus=(16*13*(left+16*right)**2)%p
                prod.append((square_plus+square_minus)%p)
            linear=sum(x*y for x,y in zip(state,beta[a*r:]))%p
            digits.append((sum(prod)+linear)%p)
            state.extend(prod)
        actual=digits[0] if t==8 else digits[0]+16*digits[1]
        expected=m//d if d else 0
        assert actual==target[m+t*d]==expected,(m,d,digits,actual,expected)
        checked+=1
report=dict(t=t,checked=checked,legal=t*(t-1),padding=t,pass_=True,
    logical_pbs=lambd+2*sum(products),
    certificate_sha256=hashlib.sha256((root/'DIVISION_CERTIFICATE.json').read_bytes()).hexdigest(),
    exported_files_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.iterdir()) if f.is_file()})
print(json.dumps(report,indent=2))
