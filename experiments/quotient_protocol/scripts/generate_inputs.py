"""Fixed public workload: ten boundary cases plus twenty seeded random cases."""
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'inputs'
OUT.mkdir(parents=True,exist_ok=True)
MASK=(1<<64)-1
SEED=20261010

class SplitMix64:
    def __init__(self,seed): self.state=seed
    def next(self):
        self.state=(self.state+0x9E3779B97F4A7C15)&MASK
        z=self.state
        z=((z^(z>>30))*0xBF58476D1CE4E5B9)&MASK
        z=((z^(z>>27))*0x94D049BB133111EB)&MASK
        return z^(z>>31)
    def below(self,n):
        limit=(1<<64)-((1<<64)%n)
        while True:
            value=self.next()
            if value<limit:return value%n

manifest={'schema':1,'seed':SEED,'generator':'SplitMix64 with rejection sampling for bounded integers',
          'measured_count':30,'warmup_count':5,
          'sampling':'10 specified boundary points followed by 20 independent public PRNG draws with replacement; not 30 uniform draws',
          'warmups':'first five boundary points, freshly encrypted each time; separate from 30 measured trials',
          'cryptographic_randomness':'fresh library/OS randomness, unrelated to public workload seed',
          'datasets':[]}
for t in (16,32,64):
    rng=SplitMix64(SEED+t)
    boundary=[(0,t-1),(1,1),(t-1,1),(t-1,t-1),(t//2-2,t-3),
              (t-2,3),(t//2-1,2),(t//2,3),(t-3,4),(t//2+1,t//2)]
    random=[(rng.below(t),1+rng.below(t-1)) for _ in range(20)]
    rows=[]
    for phase,points in [('warmup',boundary[:5]),('measured',boundary+random)]:
        for i,(m,d) in enumerate(points):
            rows.append({'phase':phase,'index':i,'t':t,'m':m,'d':d,'kind':'boundary' if phase=='warmup' or i<10 else 'seeded_random'})
    path=OUT/f'division_t{t}.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    manifest['datasets'].append({'task':f'division_t{t}','seed':SEED+t,'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':rows})
for n in (12,16):
    rng=SplitMix64(SEED+1000+n)
    allones=(1<<n)-1
    boundary=[0,1,allones^1,allones,(1<<(n//2-1))-1,(1<<(n//2))-1,(1<<(n//2+1))-1,
              sum(1<<i for i in range(0,n,2)),sum(1<<i for i in range(1,n,2)),1<<(n-1)]
    random=[rng.below(1<<n) for _ in range(20)]
    rows=[]
    for phase,points in [('warmup',boundary[:5]),('measured',boundary+random)]:
        for i,packed in enumerate(points):
            weight=packed.bit_count()
            rows.append({'phase':phase,'index':i,'n':n,'bitmask':packed,'weight':weight,
                         'threshold':int(weight>=n//2),'interval':int(n//3<=weight<=2*n//3),
                         'kind':'boundary' if phase=='warmup' or i<10 else 'seeded_random'})
    path=OUT/f'count_n{n}.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    manifest['datasets'].append({'task':f'count_n{n}','seed':SEED+1000+n,'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':rows})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({d['task']:d['sha256'] for d in manifest['datasets']},indent=2))
