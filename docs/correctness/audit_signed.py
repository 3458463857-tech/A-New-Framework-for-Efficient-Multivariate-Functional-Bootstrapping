#!/usr/bin/env python3
"""Finite-domain signed identity and every-residue FBP negacyclic check."""
from pathlib import Path
import json
def main():
 out={}
 for t in (16,32,64):
  sign=lambda x: 1 if x>=0 else -1
  canonical=lambda x: (x+t)%(2*t)-t
  residue=lambda x:x%t
  sigma=lambda x:sign(x)*(t//2)
  rho=lambda x:sign(x)*residue(x)
  psi=lambda x:x if x>=0 else -x-t
  for f in (sigma,rho,psi):
   for x in range(2*t):
    assert (f(canonical(x+t))+f(canonical(x)))%(2*t)==0
  cases=0
  for m in range(-t+1,t):
   for d in range(-t+1,t):
    if d==0:continue
    mm=t//2-sigma(m);md=t//2-sigma(d)
    am=(rho(m)+mm)%(2*t);ad=(rho(d)+md)%(2*t)
    assert am==abs(m) and ad==abs(d) and am<t and 1<=ad<t
    a=am//ad;y=canonical(mm+md+a);h=psi(y)
    expected=sign(m)*sign(d)*(abs(m)//abs(d))
    assert h==expected
    r=m-d*h
    assert abs(r)<abs(d) and (r==0 or sign(r)==sign(m))
    cases+=1
  out[t]={'signed_legal_pairs':cases,'all_results_correct':True,
          'all_2t_residues_negacyclic_for_three_functions':True,
          'scope':'Plaintext/FBP interface identities only; no signed ciphertext or noise-tail claim.'}
 path=Path(__file__).resolve().parent/'results/signed_audit.json'
 path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
