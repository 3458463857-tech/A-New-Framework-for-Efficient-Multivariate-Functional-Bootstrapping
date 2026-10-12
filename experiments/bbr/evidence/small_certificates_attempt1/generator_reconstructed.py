"""Bounded explicit BBR constructions for the frozen seven small domains.

No randomized general search and no encrypted timings. Compare a one-atom
linear encoding, small table concatenation/shared-pair encodings, and the
previous histogram-projection family. Each emitted circuit is exhausted.
"""
from pathlib import Path
from itertools import product,permutations,combinations
import argparse,hashlib,importlib.util,json,math,csv
import prepare_certificates as old
ROOT=Path(__file__).resolve().parents[1]
DEFS=ROOT/'shared_small_protocol/scripts/task_definitions.py'
spec=importlib.util.spec_from_file_location('small_tasks',DEFS)
tasks=importlib.util.module_from_spec(spec);spec.loader.exec_module(tasks)
old.tasks=tasks;old.DEFS=DEFS
P=17

class Certificate(old.Certificate):
    def pair_scores(self,score,description):
        ids=[]
        for first in range(0,self.n,2):
            if first+1<self.n:
                lut=[(score(z%3)+score(z//3))%P if z<9 else 0 for z in range(P)]
                ids.append(self.atom({first:1,first+1:3},lut,description))
            else:
                ids.append(self.atom({first:1},[score(z)%P if z<3 else 0 for z in range(P)],description+' (single last input)'))
        return ids

def histogram(task):
    c=Certificate(task);n=c.n
    hist=[(a,b,n-a-b) for a in range(n+1) for b in range(n+1-a)]
    ys=[tasks.target(task,[0]*a+[1]*b+[2]*d) for a,b,d in hist]
    directions=[(1,0),(0,1)]+[(1,k) for k in range(1,P)]
    tries=[]
    for size in [1,2,3]:
        for ds in combinations(directions,size):
            matrix=[]
            for a,b,_ in hist:
                row=[0]*(P*size)
                for j,(u,v) in enumerate(ds):row[j*P+(u*a+v*b)%P]=1
                matrix.append(row)
            values,rank=old.solve_mod(matrix,ys)
            tries.append(dict(directions=ds,rank=rank,valid=values is not None))
            if values is None:continue
            ids=[]
            for j,(u,v) in enumerate(ds):
                inner=c.pair_scores(lambda x,u=u,v=v:u if x==0 else v if x==1 else 0,'histogram projection')
                ids.append(c.atom({i:1 for i in inner},values[j*P:(j+1)*P],'function of projection sum'))
            c.output(ids);c.trace.append(dict(method='same bounded histogram-projection family',trials=tries))
            return c
    raise RuntimeError('No histogram candidate')

def direct(task):
    c=Certificate(task);domain=list(product(range(3),repeat=c.n));valid=[];count=0
    # Every task depends on each coordinate, so any zero coefficient is invalid.
    for tail in product(range(1,P),repeat=c.n-1):
        alpha=(1,)+tail;lut={};count+=1
        for xs in domain:
            key=sum(x*y for x,y in zip(alpha,xs))%P;y=tasks.target(task,list(xs))
            if key in lut and lut[key]!=y:break
            lut[key]=y
        else:valid.append((sum(a*a for a in alpha),alpha,lut))
    report=dict(method='single atom, all normalized nonzero F17 coefficients',attempts=count,valid_count=len(valid))
    if not valid:return None,report
    _,alpha,lut=min(valid,key=lambda x:(x[0],x[1]))
    idx=c.atom(dict(enumerate(alpha)),[lut.get(k,0) for k in range(P)],'direct fixed-target atom')
    c.output([idx]);report['selected_alpha']=alpha;c.trace.append(report)
    return c,report

def word_table(task):
    """Two PBS: pair -> row start, then row[start + last input].

    Six unordered pair types give at most six three-symbol output words.
    Enumerate all word orders with maximal overlap; this is only a tiny LUT
    layout construction, not a claim about minimum-cost FHE circuits.
    """
    c=Certificate(task);assert c.n==3
    pairs=list(combinations(range(3),2))+[(x,x) for x in range(3)]
    words={pair:tuple(tasks.target(task,[*pair,z]) for z in range(3)) for pair in pairs}
    unique=sorted(set(words.values()));best=None;tries=0
    for order in permutations(unique):
        seq=order[0];tries+=1
        for word in order[1:]:
            if any(seq[i:i+len(word)]==word for i in range(len(seq)-len(word)+1)):continue
            overlap=max(k for k in range(len(word)+1) if k==0 or seq[-k:]==word[:k])
            seq+=word[overlap:]
        if best is None or (len(seq),seq)<(len(best),best):best=seq
    report=dict(method='pair row-start table plus three-entry-word lookup',word_orders=tries,
                shortest_in_enumerated_layout=len(best),words=[dict(pair=p,word=w) for p,w in sorted(words.items())])
    if len(best)>P:return None,report
    starts={p:next(i for i in range(len(best)-2) if best[i:i+3]==w) for p,w in words.items()}
    inner=[starts[tuple(sorted((z%3,z//3)))] if z<9 else 0 for z in range(P)]
    idx=c.atom({0:1,1:3},inner,'pair maps to start of third-input output row')
    lut=list(best)+[0]*(P-len(best));node=c.atom({idx:1,2:1},lut,'row_start + original third symbol')
    c.output([node]);report['lookup_sequence']=best;report['pair_starts']=[dict(pair=p,start=i) for p,i in sorted(starts.items())];c.trace.append(report)
    return c,report

def shared_pair(task):
    """Three PBS candidate: identical pair table, identical pair table, sum LUT.

    Exhaust injective labels of distinguishable pair-output rows, normalized
    by affine relabeling. No assertion of global circuit optimality.
    """
    c=Certificate(task);assert c.n==4
    pairs=[(0,0),(0,1),(0,2),(1,1),(1,2),(2,2)]
    matrix=[[tasks.target(task,list(a+b)) for b in pairs] for a in pairs]
    signatures=[];classes=[]
    for row in matrix:
        key=tuple(row)
        if key not in signatures:signatures.append(key)
        classes.append(signatures.index(key))
    k=len(signatures);assert k>=2
    attempts=0;best=None
    for tail in permutations(range(2,P),k-2):
        labels=(0,1)+tail;lut={};valid=True;attempts+=1
        for i in range(6):
            for j in range(i,6):
                pos=(labels[classes[i]]+labels[classes[j]])%P;y=matrix[i][j]
                if pos in lut and lut[pos]!=y:valid=False;break
                lut[pos]=y
            if not valid:break
        if valid:best=(labels,lut);break
    report=dict(method='identical pair-label LUTs followed by a sum LUT',normalized_assignments_checked=attempts,
                distinguishable_pair_rows=k,found=best is not None)
    if best is None:return None,report
    labels,lut=best;pair_labels={pair:labels[classes[i]] for i,pair in enumerate(pairs)}
    table=[pair_labels[tuple(sorted((z%3,z//3)))] if z<9 else 0 for z in range(P)]
    a=c.atom({0:1,1:3},table,'first unordered-pair label')
    b=c.atom({2:1,3:3},table,'second unordered-pair label')
    q=c.atom({a:1,b:1},[lut.get(k,0) for k in range(P)],'target from two pair labels modulo17')
    c.output([q]);report['pair_labels']=[dict(pair=p,label=v) for p,v in pair_labels.items()];c.trace.append(report)
    return c,report


def build(task):
    h=histogram(task);candidates=[h];reports=[dict(method='histogram candidate',atoms=len(h.atoms))]
    d,record=direct(task);reports.append(record)
    if d:candidates.append(d)
    if h.n==3:a,record=word_table(task)
    else:a,record=shared_pair(task)
    reports.append(record)
    if a:candidates.append(a)
    # All candidates are exhaustively checked, including those not selected.
    for c in candidates:c.export()
    chosen=min(candidates,key=lambda c:(len(c.atoms),sum(sum(a*a for a in x['alpha']) for x in c.atoms)))
    chosen.trace.append(dict(selection='fewest atoms in the explicitly listed finite candidates; squared coefficients break ties',candidates=reports))
    result=chosen.export()
    required=0.0
    for atom in chosen.atoms:
        raw=atom['alpha'][:chosen.n];previous=atom['alpha'][chosen.n:]
        # Raw fresh errors are independent; previous PBS errors may correlate.
        # Combining these conservatively by addition does not assume independence.
        required=max(required,math.sqrt(sum(a*a for a in raw))+sum(abs(a) for a in previous))
    rows=list(csv.DictReader((ROOT/'parameters/optimizer_cjp_odd-128.csv').open()))
    selected=min((r for r in rows if int(r['p'])==17 and int(r['nu'])>=required),key=lambda r:int(r['nu']))
    result.update(author_nu=int(selected['nu']),noise_factor_requirement=required,
                  selected_author_parameter_row=selected)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False);index=[]
    for task in tasks.TASKS:
        c=build(task);file=a.output_dir/(task+'.json');file.write_text(json.dumps(c,indent=2)+'\n')
        row={k:c[k] for k in ['task_id','lambda_','exhaustive_checked','author_nu','noise_factor_requirement']}
        row['sha256']=hashlib.sha256(file.read_bytes()).hexdigest();index.append(row);print(json.dumps(row),flush=True)
    (a.output_dir/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')

if __name__=='__main__':main()
