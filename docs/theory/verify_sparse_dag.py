#!/usr/bin/env python3
"""Small exact certificates for sparse/shared DAG representations; no FHE."""
from pathlib import Path
from itertools import product
import csv, hashlib, json

HERE=Path(__file__).resolve().parent
def node(name, parents, table):
    return {'name':name,'parents':parents,'table':table}
def edge(parent, mapping):return {'parent':parent,'map':mapping}
ID={0:0,1:1};NEG={0:0,1:-1}

def equality_tree(n):
    sources=[s+str(i) for i in range(n) for s in ('x','y')]
    nodes=[node('eq'+str(i),[edge('x'+str(i),ID),edge('y'+str(i),NEG)],{-1:0,0:1,1:0}) for i in range(n)]
    current=[x['name'] for x in nodes];generation=0
    while len(current)>1:
        following=[]
        for i in range(0,len(current),2):
            if i+1==len(current):following.append(current[i]);continue
            name=f'and{generation}_{i//2}'
            nodes.append(node(name,[edge(current[i],ID),edge(current[i+1],ID)],{0:0,1:0,2:1}))
            following.append(name)
        generation+=1;current=following
    return {'inputs':sources,'nodes':nodes,'output':current[0]}

def evaluate(graph, inputs, observed=None):
    values=dict(inputs);calls={}
    for item in graph['nodes']:
        parents=item['parents']
        joint=tuple(values[e['parent']] for e in parents)
        s=sum(e['map'][v] for e,v in zip(parents,joint))
        values[item['name']]=item['table'][s]
        calls[item['name']]=calls.get(item['name'],0)+1
        if observed is not None:
            observed[item['name']]['joint'].add(joint)
            observed[item['name']]['statistics'].add(s)
            observed[item['name']]['values'].add(values[item['name']])
    assert all(v==1 for v in calls.values())
    return values[graph['output']],calls

def metrics(graph):
    depth={u:0 for u in graph['inputs']};edges=0
    for item in graph['nodes']:
        assert item['name'] not in depth
        assert all(e['parent'] in depth for e in item['parents']), 'not a topological DAG'
        depth[item['name']]=1+max(depth[e['parent']] for e in item['parents'])
        edges+=len(item['parents'])
    return {'non_source_nodes':len(graph['nodes']),'edges':edges,
            'max_fan_in':max(len(v['parents']) for v in graph['nodes']),
            'depth':depth[graph['output']],
            'R_Q':sum(max(v['table'])-min(v['table'])+1 for v in graph['nodes']),
            'R_edge':sum(len(e['map']) for v in graph['nodes'] for e in v['parents'])+
                     sum(max(v['table'])-min(v['table'])+1 for v in graph['nodes'])}

def main():
    out=HERE/'certificate';out.mkdir(exist_ok=True)
    rows=[];graphs={}
    for n in range(1,9):
        graph=equality_tree(n);m=metrics(graph);cases=0
        expected_depth=1+(n-1).bit_length()
        assert m=={'non_source_nodes':2*n-1,'edges':4*n-2,'max_fan_in':2,
                   'depth':expected_depth,'R_Q':6*n-3,'R_edge':14*n-7}
        assert expected_depth==(2*n-1).bit_length()
        for x in range(1<<n):
            for y in range(1<<n):
                inputs={s+str(i):(val>>i)&1 for i in range(n) for s,val in (('x',x),('y',y))}
                actual,calls=evaluate(graph,inputs)
                assert len(calls)==2*n-1
                mismatch=sum(inputs['x'+str(i)]!=inputs['y'+str(i)] for i in range(n))
                assert actual==int(x==y)==int(mismatch==0)==int(x-y==0)
                cases+=1
        rows.append({'n':n,'input_pairs':cases,**m,'flat_min_span':2*((1<<n)-1),
                     'flat_R_Q':(1<<(n+1))-1,'two_level_R_Q':4*n+1,
                     'R2_flat_records':4*n+(1<<(n+1))-1,'R2_two_level_records':8*n+1,
                     'R2_tree_records':10*n-3,'two_level_R_edge':10*n+1,'status':'PASS'})
        graphs[str(n)]=graph

    shared={'inputs':['a','b','c'],'nodes':[
        node('s',[edge('a',ID),edge('b',ID)],{0:0,1:1,2:2}),
        node('v',[edge('s',{0:0,1:1,2:2})],{0:0,1:1,2:1}),
        node('out',[edge('s',{0:0,1:1,2:2}),edge('v',{0:0,1:-3}),edge('c',ID)],{-2:0,-1:0,0:1,1:1})],
        'output':'out'}
    observed={v['name']:{'joint':set(),'statistics':set(),'values':set()} for v in shared['nodes']}
    shared_rows=[]
    for a,b,c in product(range(2),repeat=3):
        output,calls=evaluate(shared,{'a':a,'b':b,'c':c},observed)
        assert output==(1-a)*(1-b)+a*b*c
        assert calls['s']==1 and len(calls)==3
        shared_rows.append({'a':a,'b':b,'c':c,'output':output,'s_evaluations':calls['s']})
    root=observed['out'];assert len(root['joint'])==6
    assert root['statistics']=={-2,-1,0,1}
    grid={s-3*v+c for s in range(3) for v,c in product(range(2),repeat=2)}
    assert grid==set(range(-3,4))
    shared_certificate={'graph':shared,'observed':{v:{k:sorted(vals) for k,vals in data.items()} for v,data in observed.items()},
                        'root_joint_count':6,'cartesian_parent_count':12,'cartesian_statistics':sorted(grid),
                        'trials':shared_rows,'claim':'Interface/sharing example; not an optimality or non-foldability claim.'}
    result={'scope':'Exact integer verification n=1..8 plus 8 sparse/shared cases. General claims use the proofs in sparse_dag_zh.tex. No ciphertext execution or error-probability claim.',
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'eq_results':rows,'total_eq_pairs':sum(r['input_pairs'] for r in rows),'shared_cases':len(shared_rows)}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'graphs.json').write_text(json.dumps(graphs,indent=2)+'\n')
    (out/'shared_sparse.json').write_text(json.dumps(shared_certificate,indent=2)+'\n')
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    log=f'PASS: {result["total_eq_pairs"]} EQ pairs; 8 sparse/shared inputs; all DAGs acyclic, fan-in/depth/record formulas checked; no FHE run.\n'
    (out/'check.log').write_text(log);print(log,end='')
if __name__=='__main__':main()
