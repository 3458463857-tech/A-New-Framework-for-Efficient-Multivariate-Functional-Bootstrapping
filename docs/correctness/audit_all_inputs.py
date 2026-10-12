#!/usr/bin/env python3
"""Exact finite-domain plaintext and metadata audit; never runs encryption.

Models the pinned TFHE-rs 0.8.7 paths, including radix negation, parallel
carry propagation, sequential final addition, and many-LUT valid intervals.
Noise levels are conservative library metadata, not measured error samples.
"""
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
import argparse,csv,hashlib,json,math,re

HERE=Path(__file__).resolve().parent
MAX_NOISE=5
@dataclass
class CT:
    v:int
    d:int
    n:int

class Trace:
    def __init__(self):
        self.stages=defaultdict(lambda:{'checks':0,'max_value':0,'max_degree':0,'max_noise':0,'smallest_input_limit':15})
        self.pbs=0;self.counter=0;self.outputs=0;self.stage='input';self.calls=[]
    def check(self,x,operation,limit=15):
        assert 0<=x.v<=x.d<=limit,(self.stage,operation,x,limit)
        assert 0<=x.n<=MAX_NOISE,(self.stage,operation,x)
        k=self.stage+':'+operation;r=self.stages[k]
        r['checks']+=1;r['max_value']=max(r['max_value'],x.v)
        r['max_degree']=max(r['max_degree'],x.d);r['max_noise']=max(r['max_noise'],x.n)
        r['smallest_input_limit']=min(r['smallest_input_limit'],limit)
        return x
    def tighten(self,x,d,reason):
        # Only degree changes; the actual value is checked over the entire domain.
        return self.check(CT(x.v,d,x.n),'range proof '+reason)
    def add(self,a,b):return self.check(CT(a.v+b.v,a.d+b.d,a.n+b.n),'linear add')
    def mul(self,a,k):return self.check(CT(a.v*k,a.d*k,a.n*k),'scalar multiply')
    def lut(self,a,f,name='PBS'):
        self.check(a,name+' input');self.counter+=1;self.pbs+=int(a.n>0);self.outputs+=int(a.n>0)
        return self.check(CT(f(a.v),max(f(x) for x in range(16)),int(a.n>0)),name+' output')
    def many(self,a,fs):
        limit=16//len(fs)-1
        self.check(a,'many-LUT input',limit)
        self.counter+=1;self.pbs+=int(a.n>0);self.outputs+=len(fs)*int(a.n>0)
        return [self.check(CT(f(a.v),max(f(x) for x in range(limit+1)),int(a.n>0)),'many-LUT output') for f in fs]
    def gate(self,a,b):
        assert a.d<=1 and b.d<=3
        self.check(CT(4*a.v+b.v,4*a.d+b.d,4*a.n+b.n),'bivariate packed input',12)
        self.counter+=1;self.pbs+=int(a.n+b.n>0);self.outputs+=int(a.n+b.n>0)
        return self.check(CT(a.v*b.v,a.d*b.d,int(a.n+b.n>0)),'bit-times-digit range')

def trivial(v=0):return CT(v,v,0)
def fresh(v,d=15):return CT(v,d,1)
def value(blocks):return sum(x.v*4**i for i,x in enumerate(blocks))
def nominal(blocks):
    assert all(x.d<=3 and x.n<=1 for x in blocks)

def radix_sub(tr,a,b):
    nominal(a);nominal(b);n=len(a);assert 4<=n<=6
    # radix/neg.rs:101; no PBS and no noise reduction.
    neg=[];zb=0
    for x in b:
        z=4*max(1,math.ceil((x.d+zb)/4))
        neg.append(tr.check(CT(z-x.v-zb,z-zb,x.n),'radix negation'))
        zb=z//4
    # At eight workers, the library latency selector takes the parallel branch.
    sums=[tr.add(x,y) for x,y in zip(a,neg)]
    shifted=[];states=[]
    for i,x in enumerate(sums):
        if i==n-1:
            f=lambda z: (2 if z>=4 else 1 if z==3 else 0)<<1
        elif i==0:
            f=lambda z:int(z>=4)
        elif i<4:
            f=lambda z,i=i:(2 if z>=4 else 1 if z==3 else 0)<<(i-1)
        else:
            f=lambda z,i=i:(2 if z>=4 else 1 if z==3 else 0)<<(i%4)
        state,shift=tr.many(x,[f,lambda z:(z%4)<<1])
        states.append(state);shifted.append(shift)
    states.pop() # Last flag is unused; its extraction is counted conservatively.
    cumulative=[]
    for offset in range(0,len(states),4):
        group=states[offset:offset+4];acc=group[0];cumulative.append(acc)
        for x in group[1:]:acc=tr.add(acc,x);cumulative.append(acc)
    resolved=[]
    for i,x in enumerate(cumulative):
        if i<4:
            f=(lambda z:(z>>3)&1) if i%4==3 else (lambda z,i=i:2*((z>>i)&1))
        else:
            j=i%4
            f=lambda z,j=j:2 if z>=(2<<j) else 1 if (z&((2<<j)-1))==((2<<j)-1) else 0
        resolved.append(tr.lut(x,f,'carry-state PBS'))
    simulators=[trivial()];groups=[]
    for x in resolved:
        if len(simulators)%4==0:groups.append(x);simulators.append(trivial(1))
        else:simulators.append(x)
    # For n<=6 there is at most one inter-group carry; no Hillis-Steele path.
    assert len(groups)<=1
    carries=[trivial()]+groups
    out=[tr.lut(tr.add(tr.add(x,simulators[i]),carries[i//4]),lambda z:(z>>1)%4,'radix cleanup PBS') for i,x in enumerate(shifted)]
    nominal(out);assert value(out)==(value(a)-value(b))%(4**n)
    return out

def radix_add3(tr,a,b):
    nominal(a);nominal(b);assert len(a)==len(b)==3
    # At eight workers 3 < 3 is false, so the sequential >=4-bit path is selected.
    out=[];carry=trivial()
    for x,y in zip(a,b):
        z=tr.add(tr.add(x,y),carry)
        out.append(tr.lut(z,lambda v:v%4,'message extraction'))
        carry=tr.lut(z,lambda v:v//4,'carry extraction')
    nominal(out);assert value(out)==(value(a)+value(b))%64
    return out

def exact_tables(t,m):
    ns=[x**m for x in range(1,t)]
    return [0]+[n.bit_length()-int(n&(n-1)==0)+1 for n in ns],[1]+[n.bit_length() for n in ns]

def parse_config(s,t):
    m,nb={32:(44,5),64:(89,6)}[t];ceil,floor=exact_tables(t,m);off=max(floor[1:]);mx=off+ceil[-1]-1
    text=s[s.index('let grouped_rows:'):s.index('let last_outer_row')]
    sub=text.split(f'{t} => &[',1)[1].split('\n        ],',1)[0]
    rows=[list(map(int,re.findall(r'\d+',a))) for a in re.findall(r'&\[([^]]+)\]',sub)]
    thresholds=[off+ceil[x]-1 for x in range(1,t)]
    base=[sum(q<=r*16 for q in thresholds) for r in range(mx//16+1)]
    branch=s.split(f'if t == {t} {{',1)[1]
    override=branch.split('] {',1)[0]
    for row,v in re.findall(r'\((\d+), (\d+)\)',override):base[int(row)]=int(v)
    reachable=defaultdict(dict)
    for a in range(t):
        for b in range(1,t):
            delta=ceil[a]+off-floor[b];r,l=divmod(delta,16);res=a//b-base[r]
            assert res>=0
            assert l not in reachable[r] or reachable[r][l]==res
            reachable[r][l]=res
    groups=[];selectors=[]
    for rs in rows:
        high=rs[0]//16;assert all(r//16==high for r in rs)
        assigned={}
        for r in rs:
            for l,v in reachable[r].items():assert l not in assigned or assigned[l]==v;assigned[l]=v
        vals=[assigned.get(i,0) for i in range(16)];mids=sorted(r%16 for r in rs)
        if mids not in selectors:selectors.append(mids)
        groups.append({'high':high,'values':vals,'max':max(vals),'selector':selectors.index(mids)})
    bins=[]
    for j in sorted(range(len(groups)),key=lambda i:-groups[i]['max']):
        d=groups[j]['max'];nn=(d+2)//3
        found=next((b for b in bins if b[0]+d<=15 and b[1]+nn<=5),None)
        if found:found[0]+=d;found[1]+=nn;found[2].append(j)
        else:bins.append([d,nn,[j]])
    return dict(t=t,m=m,nb=nb,ceil=ceil,floor=floor,off=off,mx=mx,base=base,groups=groups,selectors=selectors,bins=[b[2] for b in bins],maxres=max(g['max'] for g in groups),highs=list(range(groups[0]['high'],mx//256+1)))

def classified(tr,input_ct,values):
    if not any(values):return ('zero',trivial())
    if len(set(values))==1:return ('constant',values[0])
    return ('variable',tr.lut(input_ct,lambda x:values[x]))

def transform(tr,c,x,table):
    low=fresh(x%16);high=fresh(x//16,c['t']//16-1)
    eq=([tr.lut(high,lambda z:int(z==0)),tr.tighten(high,1,'binary high')]
        if c['t']==32 else tr.many(high,[lambda z,i=i:int(z==i) for i in range(4)]))
    out=[]
    for b in range(c['nb']):
        branches=[]
        for j in range(c['t']//16):
            vals=[(table[j*16+l]//4**b)%4 for l in range(16)]
            kind,obj=classified(tr,low,vals)
            branches.append(obj if kind=='zero' else tr.mul(eq[j],obj) if kind=='constant' else tr.gate(eq[j],obj))
        acc=branches[0]
        for x in branches[1:]:acc=tr.add(acc,x)
        acc=tr.tighten(acc,3,'exclusive input branches')
        out.append(tr.lut(acc,lambda z:z%4,'input refresh'))
    nominal(out);return out

def pack(tr,a,b):return tr.add(tr.mul(b,4),a)

def outer(tr,c,blocks):
    low=pack(tr,blocks[0],blocks[1]);mid=pack(tr,blocks[2],blocks[3])
    high=blocks[4] if len(blocks)==5 else pack(tr,blocks[4],blocks[5])
    high=tr.tighten(high,c['mx']//256,'shifted difference upper bound')
    highs=c['highs']
    eq=([tr.lut(high,lambda z:int(z==0)),tr.tighten(high,1,'binary outer high')] if highs==[0,1] else tr.many(high,[lambda z,h=h:int(z==h) for h in highs]))
    mids=[tr.lut(mid,lambda z,ms=ms:int(z in ms)) for ms in c['selectors']]
    bases=[]
    for digit in range(3):
        branches=[]
        for j,h in enumerate(highs):
            vals=[(c['base'][h*16+v]//4**digit)%4 if h*16+v<len(c['base']) else 0 for v in range(16)]
            kind,obj=classified(tr,mid,vals)
            branches.append(obj if kind=='zero' else tr.mul(eq[j],obj) if kind=='constant' else tr.gate(eq[j],obj))
        acc=branches[0]
        for x in branches[1:]:acc=tr.add(acc,x)
        acc=tr.tighten(acc,3,'exclusive outer base branches')
        bases.append(tr.lut(acc,lambda z:z%4,'outer base refresh'))
    groupvals=[]
    for g in c['groups']:
        cond=tr.gate(eq[highs.index(g['high'])],mids[g['selector']])
        parts=[]
        for j in range((g['max']+2)//3):
            digit=tr.lut(low,lambda z,j=j,g=g:min(3,max(0,g['values'][z]-3*j)))
            parts.append(tr.gate(cond,digit))
        acc=parts[0]
        for x in parts[1:]:acc=tr.add(acc,x)
        groupvals.append(tr.tighten(acc,g['max'],'residual component reconstruction'))
    current=[]
    for bin_ in c['bins']:
        acc=groupvals[bin_[0]]
        for j in bin_[1:]:acc=tr.add(acc,groupvals[j])
        current.append(tr.lut(acc,lambda z:min(z,c['maxres']),'residual bin refresh'))
    while len(current)>2:
        current=[tr.lut(tr.add(*current[i:i+2]),lambda z:min(z,c['maxres']),'residual tree refresh') if i+1<len(current) else current[i] for i in range(0,len(current),2)]
    acc=current[0]
    for x in current[1:]:acc=tr.add(acc,x)
    acc=tr.tighten(acc,c['maxres'],'exclusive residual groups')
    split=([tr.lut(acc,lambda z,i=i:(z//4**i)%4) for i in range(2)] if c['t']==32 else tr.many(acc,[lambda z:z%4,lambda z:z//4]))
    tr.stage='final_radix_add'
    return radix_add3(tr,bases,split+[trivial()])

def t16(tr,m,d):
    ceil,floor=exact_tables(16,22)
    tr.stage='inner_transform'
    a=[tr.lut(fresh(m),lambda z,i=i:(ceil[z]+86)//4**i%4) for i in range(4)]
    b=[tr.lut(fresh(d),lambda z,i=i:floor[z]//4**i%4) for i in range(4)]
    tr.stage='radix_subtraction';delta=radix_sub(tr,a,b)
    assert value(delta)==ceil[m]+86-floor[d]
    tr.stage='outer_recovery';low=pack(tr,*delta[:2]);high=pack(tr,*delta[2:])
    basevals=[0]*6+[1,2,3,6,9]+[0]*5
    base=tr.lut(high,lambda z:basevals[z])
    eq=[tr.lut(high,lambda z,h=h:int(z==h)) for h in range(5,11)]
    thresholds=[[6],[12],[9],[2,10,15],[4,8,12],[0,3,5],[8,10,12]]
    digs=[tr.lut(low,lambda z,ts=ts:sum(z>=q for q in ts)) for ts in thresholds]
    gates=[tr.gate(eq[min(i,5)],x) for i,x in enumerate(digs)]
    first=base
    for x in gates[:4]:first=tr.add(first,x)
    result=tr.lut(first,lambda z:min(z,9),'partial refresh')
    second=gates[4]
    for x in gates[5:]:second=tr.add(second,x)
    second=tr.tighten(second,6,'last two exclusive high rows')
    tr.stage='final_output';result=tr.lut(tr.add(result,second),lambda z:z,'identity refresh')
    assert result.v==m//d and result.n<=1
    return result.v

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-dir',default=str(HERE/'code'));args=parser.parse_args()
    src=Path(args.source_dir);s=(src/'algorithm1_audited.rs').read_text(encoding='utf-8-sig')
    s16=(src/'algorithm1_t16_audited.rs').read_text(encoding='utf-8-sig')
    ceil16,floor16=exact_tables(16,22)
    for name,expected in [('CEIL_LOG_SHIFTED',ceil16),('FLOOR_LOG_SHIFTED',floor16),('CEIL_LOG_WITH_OFFSET',[x+86 for x in ceil16])]:
        body=re.search(rf'const {name}: \[u64; 16\] = \[([^]]+)\]',s16).group(1)
        actual=[int(x) for x in body.split(',') if x.strip()]
        assert actual==expected,(name,actual,expected)
    configs={t:parse_config(s,t) for t in (32,64)}
    # Certify actual fixed Rust arrays against exact integer powers.
    for t,c in configs.items():
        for fn,expected in [('shifted_ceil',c['ceil']),('shifted_floor',c['floor'])]:
            function=s.split('fn '+fn+'(',1)[1].split('fn ',1)[0]
            actual=list(map(int,re.search(rf"{c['m']} => \[([^]]+)\]",function).group(1).split(',')))
            assert actual==expected,(t,fn)
    outdir=HERE/'results';outdir.mkdir(exist_ok=True)
    summary={};allrows=[]
    for t in (16,32,64):
        aggregate={};counts=set();output_counts=set();counters=set()
        for m in range(t):
            for d in range(1,t):
                tr=Trace()
                if t==16:actual=t16(tr,m,d)
                else:
                    c=configs[t];tr.stage='inner_transform'
                    a=transform(tr,c,m,[x+c['off'] for x in c['ceil']]);b=transform(tr,c,d,c['floor'])
                    tr.stage='radix_subtraction';delta=radix_sub(tr,a,b)
                    assert value(delta)==c['ceil'][m]+c['off']-c['floor'][d]
                    tr.stage='outer_recovery';result=outer(tr,c,delta);actual=value(result)
                assert actual==m//d,(t,m,d,actual)
                counts.add(tr.pbs);output_counts.add(tr.outputs);counters.add(tr.counter)
                allrows.append([t,m,d,actual,tr.counter,tr.pbs,tr.outputs])
                for stage,values in tr.stages.items():
                    if stage not in aggregate:aggregate[stage]=values.copy()
                    else:
                        target=aggregate[stage]
                        for k,v in values.items():target[k]=(target[k]+v if k=='checks' else min(target[k],v) if k=='smallest_input_limit' else max(target[k],v))
        summary[str(t)]={'legal_pairs':t*(t-1),'all_plaintext_results_correct':True,'all_metadata_preconditions_pass':True,'predicted_library_pbs_counter':sorted(counters),'predicted_nontrivial_blind_rotations':sorted(counts),'conservative_scalar_output_events':sorted(output_counts),'stage_budget':aggregate}
    with (outdir/'all_input_checks.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['t','m','d','quotient','library_counter_including_trivial','nontrivial_blind_rotations','conservative_scalar_output_events']);w.writerows(allrows)
    result={'scope':'Finite-domain exact plaintext and TFHE metadata simulation; not an encrypted experiment, not a strict error-tail proof. All valid pairs, not a 30-case inference.',
            'source_sha256':{p.name:sha(p) for p in src.glob('algorithm1*_audited.rs')},'domains':summary}
    (outdir/'all_input_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({t:{k:v for k,v in row.items() if k!='stage_budget'} for t,row in summary.items()},indent=2))

if __name__=='__main__':main()
