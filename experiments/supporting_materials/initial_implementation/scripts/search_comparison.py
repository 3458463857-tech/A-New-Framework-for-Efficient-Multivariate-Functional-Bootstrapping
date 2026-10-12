#!/usr/bin/env python3
"""Budget-matched public offline search; no encrypted timings are produced.

All methods use the same bounded normalized symmetric row space and energy as
the supplied anneal_symmetric implementation. Histogram aggregation exactly
preserves the multiplicity of every Cartesian input; returned rows are also
verified by the original independent full-domain verifier.
"""
import argparse
import csv
import gzip
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code/Section4_Code/chapter4_compression"))
from compress import verify, _symmetric_energy

def target(name, point):
    if name == "lower_median":
        return sorted(point)[(len(point)-1)//2]
    counts = Counter(point)
    return min(counts, key=lambda x: (-counts[x], x))

def histogram_data(ell, t, name):
    data = Counter((tuple(point.count(i) for i in range(t)), target(name, point))
                   for point in itertools.product(range(t), repeat=ell))
    return [(h, out, count) for (h, out), count in sorted(data.items())]

def energy(row, data, ell, n):
    bins = {}
    for h, output, count in data:
        z = sum(a*b for a,b in zip(row, h))
        bucket = bins.setdefault(z, {})
        bucket[output] = bucket.get(output, 0) + count
    conflicts = sum(sum(b.values()) - max(b.values()) for b in bins.values())
    span = ell*(max(row)-min(row))
    return conflicts*n*(ell*max(max(row),1)+1)+span, span, conflicts == 0

def normalize(row):
    m=min(row)
    return [x-m for x in row]

def execute(method, seed, ell, t, name, budget, max_score, trace):
    rng=random.Random(seed)
    data=histogram_data(ell,t,name)
    points=list(itertools.product(range(t),repeat=ell))
    outputs=[target(name,p) for p in points]
    current=normalize([rng.randrange(max_score+1) for _ in range(t)])
    cur_e,cur_s,cur_v=energy(current,data,ell,t**ell)
    best=current[:] if cur_v else None
    best_span=cur_s if cur_v else math.inf
    temperature=100.0
    stale=0
    valid=0
    started=time.perf_counter()
    # Includes the initial objective evaluation in the shared budget.
    for evaluation in range(budget):
        if evaluation==0:
            candidate=current[:]
        elif method=="random":
            candidate=normalize([rng.randrange(max_score+1) for _ in range(t)])
        else:
            candidate=current[:]
            i=rng.randrange(t)
            candidate[i]=min(max_score,max(0,candidate[i]+rng.choice((-2,-1,1,2))))
            candidate=normalize(candidate)
        e,s,v=energy(candidate,data,ell,t**ell)
        # Audit optimized objective against the source objective on first and
        # last proposal (full equivalence is checked separately below).
        if evaluation in (0,budget-1):
            assert (e,s,v)==_symmetric_energy(candidate,points,outputs,ell)
        delta=e-cur_e
        accept=(method=="random" or delta<=0 or
                (method=="sa" and rng.random()<math.exp(-delta/max(temperature,1e-12))))
        if accept:
            current,cur_e,cur_s,cur_v=candidate,e,s,v
        if v:
            valid+=1
            if s<best_span:
                best,best_span=candidate[:],s
                stale=0
            else:
                stale+=1
        else:
            stale+=1
        trace.writerow([name,ell,t,method,seed,evaluation,e,s,int(v),int(accept),
                        "" if best is None else best_span,": ".join(map(str,candidate))])
        temperature*=0.9995
        if stale>=2000:
            temperature=max(temperature,50.0)
            stale=0
    elapsed=time.perf_counter()-started
    report=verify([best[:] for _ in range(ell)],t,lambda p:target(name,p)) if best else None
    assert report is None or (report.valid and report.span==best_span)
    return {"function":name,"ell":ell,"t":t,"method":method,"seed":seed,
            "objective_evaluations":budget,"max_score":max_score,
            "found_valid":best is not None,"best_span":None if best is None else best_span,
            "row":best,"valid_proposals":valid,"search_seconds":elapsed,
            "exhaustive_inputs":t**ell if best else 0,"verified":report.valid if report else False}

def bounded_optimum(ell,t,name,max_score):
    data=histogram_data(ell,t,name)
    best=math.inf
    rows=[]
    checked=0
    for row in itertools.product(range(max_score+1),repeat=t):
        if min(row)!=0:
            continue
        checked+=1
        _,s,v=energy(row,data,ell,t**ell)
        if v and s<=best:
            if s<best:
                rows=[]
            rows.append(row)
            best=s
    return {"function":name,"ell":ell,"t":t,"max_score":max_score,
            "normalized_rows_checked":checked,"minimum_span":None if math.isinf(best) else best,
            "optimal_rows":rows,"scope":"only symmetric rows with entries in [0,max_score]"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--budget",type=int,default=2000)
    p.add_argument("--seeds",type=int,default=10)
    args=p.parse_args()
    if args.output_dir.exists() and (not args.output_dir.is_dir() or any(args.output_dir.iterdir())):
        p.error(f"refusing to overwrite nonempty output path: {args.output_dir}")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=[("lower_median",6,3),("lower_median",4,4),("mode_smallest_tie",4,3)]
    results=[]
    with gzip.open(args.output_dir/"all_proposals.csv.gz","wt",newline="",encoding="utf-8") as f:
        trace=csv.writer(f)
        trace.writerow(["function","ell","t","method","seed","evaluation","energy","span","valid","accepted","best_span","row"])
        for name,ell,t in cases:
            for method in ("sa","greedy","random"):
                for seed in range(20261010,20261010+args.seeds):
                    result=execute(method,seed,ell,t,name,args.budget,12,trace)
                    results.append(result)
                    print(json.dumps(result),flush=True)
    optima=[bounded_optimum(ell,t,name,12) for name,ell,t in cases]
    with (args.output_dir/"runs.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
    summaries=[]
    for name,ell,t in cases:
        for method in ("sa","greedy","random"):
            rr=[r for r in results if (r["function"],r["ell"],r["t"],r["method"])==(name,ell,t,method)]
            spans=[r["best_span"] for r in rr if r["found_valid"]]
            summaries.append({"function":name,"ell":ell,"t":t,"method":method,"seeds":len(rr),
                "budget_per_seed":args.budget,"successful_seeds":len(spans),"min_span":min(spans) if spans else None,
                "median_span":statistics.median(spans) if spans else None,"max_span":max(spans) if spans else None,
                "median_seconds":statistics.median(r["search_seconds"] for r in rr)})
    with (args.output_dir/"summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0])); w.writeheader(); w.writerows(summaries)
    (args.output_dir/"results.json").write_text(json.dumps({"settings":{"temperature":100,"cooling":0.9995,
        "reheat_interval":2000,"reheat_temperature_floor":50,"neighborhood":[-2,-1,1,2],
        "restarts":1,"budget_includes_initial":True,"negative_states":"clamp then normalize",
        "invalid_states":"penalized; allowed during search; never returned as a valid solution"},
        "runs":results,"summary":summaries,"bounded_optima":optima},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
