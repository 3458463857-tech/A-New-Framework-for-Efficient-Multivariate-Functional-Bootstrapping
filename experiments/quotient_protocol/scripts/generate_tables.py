"""Generate paper rows only from validated final summaries (no historical mixing)."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--protocol',default='protocol1',help='Explicit suite prefix to select; defaults to the published batch.')
args=parser.parse_args()
data=json.loads((ROOT/'summary/all_results.json').read_text())
selected=[r for r in data['runs'] if r['run'].startswith(args.protocol+'_')]
assert len(selected)==15,f'Expected 15 rows for protocol {args.protocol}, got {len(selected)}'
runs={ (r['method'],int(r['size']),r['predicate']):r for r in selected }
assert len(runs)==15, f'Expected all 15 successful configurations, got {len(runs)}'
def timing(r):return f"${r['mean_ms']:.2f} \\pm {r['population_sd_ms']:.2f}$"
out=ROOT/'summary'
count_rows=[]
for n in (12,16):
    for predicate in ('threshold','interval'):
        ours=runs['count',n,predicate];ref=runs['refined_count',n,predicate]
        assert ours['input_manifest_sha256']==ref['input_manifest_sha256']
        count_rows.append(f"{n} & {predicate} & {timing(ours)} & {timing(ref)} \\\\")
(out/'count_rows.tex').write_text('% n, predicate, DCC mean+/-populationSD (ms), Refined Boolean-CBS+full-LUT mean+/-SD (ms)\n'+'\n'.join(count_rows)+'\n',encoding='utf-8')
division_rows=[]
for t in (16,32,64):
    ours=runs['dcc',t,'none'];native=runs['native',t,'none']
    assert ours['input_manifest_sha256']==native['input_manifest_sha256']
    assert ours['pbs_count']['min']==ours['pbs_count']['max']
    assert native['pbs_count']['min']==native['pbs_count']['max']
    refined=timing(runs['refined_div',16,'none']) if t==16 else '--'
    division_rows.append(f"{t} & {timing(ours)} & {ours['pbs_count']['mean']:.0f} & {timing(native)} & {native['pbs_count']['mean']:.0f} & {refined} \\\\")
(out/'division_rows.tex').write_text('% t, DCC ms, library-counted PBS, native ms, library-counted PBS, Refined DIV ms\n'+'\n'.join(division_rows)+'\n',encoding='utf-8')
resources=[]
for n in (12,16):
    resources.extend([
        {'n':n,'method':'DCC','logical_records':3*n+1,'logical_source':'explicit identity-score construction; unelided inner records',
         'public_buffer_coefficient_bytes':2*8192*8,'buffer_source':'structural allocation calculation: one GLWE accumulator, (k+1)*N u64 coefficients',
         'key_serialized_bytes':'not separately measured','isolated_query_scratch_bytes':'not separately measured'},
        {'n':n,'method':'Refined Boolean CBS + full LUT','logical_records':1<<n,'logical_source':'complete n-bit LUT',
         'public_buffer_coefficient_bytes':(1<<n)*8,'buffer_source':'actual logged PolynomialList u64 coefficient count',
         'key_serialized_bytes':'not separately measured','isolated_query_scratch_bytes':'not separately measured'}])
with (out/'resource_scopes.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=resources[0]);w.writeheader();w.writerows(resources)
print('Generated final paper rows and resource-scope table from 15 validated configurations.')
