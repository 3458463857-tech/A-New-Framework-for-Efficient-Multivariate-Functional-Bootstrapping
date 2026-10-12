"""Generate fixed shared inputs; exhaust the small plaintext domains. No FHE."""
import csv, hashlib, itertools, json
from pathlib import Path
from task_definitions import TASKS,target,score
ROOT=Path(__file__).resolve().parents[1]
MASK=(1<<64)-1
class SplitMix64:
    def __init__(self,seed):self.state=seed
    def next(self):
        self.state=(self.state+0x9E3779B97F4A7C15)&MASK;z=self.state
        z=((z^(z>>30))*0xBF58476D1CE4E5B9)&MASK;z=((z^(z>>27))*0x94D049BB133111EB)&MASK
        return z^(z>>31)
    def uniform(self,bound):
        limit=(1<<64)-((1<<64)%bound)
        while True:
            x=self.next()
            if x<limit:return x%bound
def boundaries(n):
    if n==3:return [[0,0,0],[1,1,1],[2,2,2],[0,1,2],[0,0,1],[0,1,1],[0,0,2],[0,2,2],[1,1,2],[1,2,2]]
    return [[0,0,0,0],[1,1,1,1],[2,2,2,2],[0,0,1,1],[1,1,2,2],[0,0,2,2],[0,0,1,2],[0,1,1,2],[0,1,2,2],[0,0,0,2]]
def main():
    out=ROOT/'inputs';out.mkdir(exist_ok=True);manifest=[];certificates=[]
    for task,(t,n) in TASKS.items():
        seed=20261010+1000*t+n;rng=SplitMix64(seed)
        rows=[]
        for i in range(5):
            xs=[(j+i)%t for j in range(n)];rows.append(['warmup',i,task,xs,target(task,xs),'cyclic_warmup'])
        for i,xs in enumerate(boundaries(n)):rows.append(['measured',i,task,xs,target(task,xs),'boundary_histogram_'+str(i)])
        for i in range(20):
            xs=[rng.uniform(t) for _ in range(n)];rows.append(['measured',i+10,task,xs,target(task,xs),'splitmix64_uniform'])
        path=out/(task+'.csv')
        with path.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f,lineterminator='\n');w.writerow(['phase','index','task_id','inputs','expected','kind'])
            for ph,i,task,xs,y,kind in rows:w.writerow([ph,i,task,';'.join(map(str,xs)),y,kind])
        values={};hist={};count=0
        for xs in itertools.product(range(t),repeat=n):
            z=score(task,xs);y=target(task,xs);h=tuple(xs.count(x) for x in range(t))
            assert z not in hist or hist[z]==h
            assert z not in values or values[z]==y
            hist[z]=h;values[z]=y;count+=1
        assert max(values)==n*(n+1)
        certificates.append(dict(task_id=task,cartesian_inputs=count,weights=[n+1,0,n],span=n*(n+1),histograms=len(hist),outer_table={str(k):v for k,v in sorted(values.items())},result='PASS'))
        manifest.append(dict(task_id=task,t=t,n=n,file=path.name,seed=seed,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),warmups=5,boundary_samples=10,random_samples=20,measured=30))
    defs=Path(__file__).with_name('task_definitions.py')
    (out/'manifest.json').write_text(json.dumps(dict(protocol='seven_small_ternary_instances',definitions_sha256=hashlib.sha256(defs.read_bytes()).hexdigest(),files=manifest),indent=2)+'\n')
    (out/'plaintext_certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
    print(json.dumps(dict(tasks=len(manifest),rows=35*len(manifest),exhaustive_inputs=sum(c['cartesian_inputs'] for c in certificates),result='PASS')))
if __name__=='__main__':main()
