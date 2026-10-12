"""Exact integer check of the two-level bitstring comparison construction.
This verifies finite instances, not the all-n lower-bound proof in the paper.
No homomorphic latency or cryptographic failure probability is inferred.
"""
from pathlib import Path
import argparse, csv, json, hashlib

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    results=[]
    for n in range(1,9):
        count=0
        for x in range(1<<n):
            for y in range(1<<n):
                mismatch=sum(int(((x>>i)&1)!=((y>>i)&1)) for i in range(n))
                assert (mismatch==0)==(x==y)
                assert mismatch==(x^y).bit_count()
                assert ((x-y)==0)==(x==y)
                # All thresholds and intervals are functions of this same count.
                for threshold in range(n+1):
                    assert (mismatch>=threshold)==((x^y).bit_count()>=threshold)
                count+=1
        results.append({'n':n,'input_pairs_checked':count,'flat_min_span':2*((1<<n)-1),
                        'flat_min_dense_records':4*n+(1<<(n+1))-1,
                        'nested_dense_records':8*n+1,'nested_pure_lut_entries':4*n+1,
                        'status':'PASS'})
    (out/'summary.json').write_text(json.dumps({'scope':'finite exhaustive integer validation n=1..8; general proof is in manuscript','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':results},indent=2),encoding='utf-8')
    with (out/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=results[0].keys());writer.writeheader();writer.writerows(results)
    print('PASS:',sum(x['input_pairs_checked'] for x in results),'input pairs; no FHE benchmark')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
