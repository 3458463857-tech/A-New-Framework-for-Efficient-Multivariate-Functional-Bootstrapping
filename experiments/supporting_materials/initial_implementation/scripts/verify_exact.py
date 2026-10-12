#!/usr/bin/env python3
"""Integer-only independent division and explicit count-representation audit."""
import argparse
import datetime
import csv
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"code/Section4_Code/chapter4_compression"))
from compress import verify,indicator_representation

def exact_logs(x,M):
    # floor(M log_2 x) = floor(log_2(x**M)); exact integer bit length.
    power=x**M
    floor=power.bit_length()-1
    ceil=floor+int(power!=(1<<floor))
    return floor,ceil

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path)
    a=p.parse_args()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out=a.output_dir or ROOT/"results"/("exact_audit_"+stamp)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        p.error(f"refusing to overwrite nonempty output path: {out}")
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for t,M in ((16,22),(32,44),(64,89)):
        floor=[0]+[exact_logs(x,M)[0] for x in range(1,t)]
        ceil=[-1]+[exact_logs(x,M)[1] for x in range(1,t)]
        mismatches=[]
        float_mismatches=[]
        deltas=[]
        for x in range(1,t):
            if (math.floor(M*math.log2(x)),math.ceil(M*math.log2(x)))!=(floor[x],ceil[x]):
                float_mismatches.append(x)
        for m in range(t):
            for d in range(1,t):
                delta=ceil[m]-floor[d]
                actual=sum(delta>=ceil[q] for q in range(1,t))
                deltas.append(delta)
                if actual!=m//d: mismatches.append([m,d,actual,m//d])
        assert not mismatches and not float_mismatches
        results.append({"case":f"division_t{t}","t":t,"ell":2,"M":M,"inputs":t*(t-1),
            "correct":True,"method":"exact integer powers and bit length; no floating logarithms",
            "delta_min":min(deltas),"delta_max":max(deltas),"float_table_mismatches":float_mismatches,
            "floor":floor,"ceil":ceil})
    for ell,lower,upper in ((6,2,4),(10,4,6)):
        rep=indicator_representation(ell,2,{1})
        v=verify(rep,2,lambda p:int(lower<=sum(p)<=upper))
        assert v.valid
        results.append({"case":f"hamming_interval_l{ell}","t":2,"ell":ell,"inputs":2**ell,
            "correct":True,"method":"explicit p_i=(0,1), exhaustive verifier","span":v.span,
            "distinct_sums":v.distinct_sums,"stored_records_ungrouped":2*ell+v.span+1,
            "direct_records":2**ell,"lower":lower,"upper":upper})
    (out/"results.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    fields=sorted(set().union(*(set(r)-{"floor","ceil"} for r in results)))
    with (out/"summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(results)
    for r in results: print(json.dumps({k:v for k,v in r.items() if k not in ("floor","ceil")}))

if __name__=="__main__":main()
