"""Build the positive function catalogue from existing records, without experiments.

The first run imports the v1 selected-results snapshot. Subsequent runs can use
the local snapshot without a v1 checkout. No timing or accuracy experiment runs.
"""
from pathlib import Path
import csv
import hashlib
import json

HERE=Path(__file__).resolve().parent
V1=HERE.parents[1]/'DCC_revision_2026-10-10_v1'
SOURCE=V1/'05_Reproducibility/code/Reproduction_Materials_for_Application_function/results/results.json'
SNAPSHOT=HERE/'FUNCTION_CATALOGUE_SOURCE_SELECTED.json'

def main():
    if not SNAPSHOT.exists():
        source=json.loads(SOURCE.read_text(encoding='utf-8'))
        snapshot=dict(source_path=str(SOURCE.relative_to(V1)),
            source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            generated_utc=source['generated_utc'],metric=source['metric'],
            selection_rule=source['selection_rule'],
            imported_without_rerun=True,selected=source['selected'])
        SNAPSHOT.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    snapshot=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    rows=[]
    def add(**kw):
        row=dict(id='',family_zh='',function='',domain='',representation='',evidence_level='',
            analytic_construction='',finite_check='',checked_inputs='',structural_baseline='',
            baseline_records='',construction_records='',metric='',encrypted_runtime_advantage='',
            source='',note='')
        row.update(kw);rows.append(row)
    # One proof supports the whole family: equal Hamming weight means an equal
    # input orbit under permutations, so every binary symmetric target is Q(S).
    for key,name,q in [
        ('threshold','阈值','Q(s)=1[s>=tau]'),
        ('interval','区间','Q(s)=1[a<=s<=b]'),
        ('exact_count','精确计数谓词','Q(s)=1[s=k]'),
        ('majority','多数表决','Q(s)=1[s>n/2], with the stated tie rule'),
        ('mod_k','计数模 k','Q(s)=s mod k'),
        ('parity','奇偶校验','Q(s)=s mod 2'),
        ('count_bucket','分桶或截断计数','arbitrary finite Q on {0,...,n}'),
        ('binary_symmetric','任意二元对称函数','Q(s)=f(1 repeated s times,0 repeated n-s times)')]:
        add(id='A_'+key,family_zh='二元计数统计',function=name,domain='[2]^n',
            representation='single additive statistic S=sum_i x_i',
            evidence_level='已证明构造',analytic_construction='yes; common count-statistic proof',
            finite_check='family proof; no new parameter grid',
            structural_baseline='direct LUT, where 3n+1<2^n',baseline_records='2^n',
            construction_records='3n+1',metric='dense inner+outer records; linear identity inner tables can be omitted in an optimized implementation',
            encrypted_runtime_advantage='未据此主张',source='FUNCTION_CATALOGUE.md#统一构造',note=q)
    add(id='A_symbol_count',family_zh='符号集合计数统计',function='阈值、区间、精确计数、计数模 k及任意计数映射',
        domain='[t]^n, A subset of [t]',representation='S=sum_i 1[x_i in A]; f=Q(S)',
        evidence_level='已证明构造',analytic_construction='yes; indicator count statistic',
        finite_check='family proof plus selected certified instances below',
        structural_baseline='direct LUT, where nt+n+1<t^n',baseline_records='t^n',
        construction_records='nt+n+1',metric='dense inner+outer records',
        encrypted_runtime_advantage='未据此主张',source='FUNCTION_CATALOGUE.md#统一构造',
        note='All Q on counts {0,...,n} share the same inner maps; no simulated annealing is needed.')
    add(id='A_ternary_histogram',family_zh='三符号频率统计',function='任意依赖直方图的函数，包括众数、下中位数、不同符号数及频率矩',
        domain='[3]^n, n<=6',representation='S=7c0+5c2; inner row (7,0,5)',
        evidence_level='已证明构造',analytic_construction='yes; S uniquely determines the histogram for n<=6',
        finite_check='mode/median instances n=5,6 certified below',
        structural_baseline='direct LUT, where 10n+1<3^n',baseline_records='3^n',
        construction_records='10n+1',metric='dense inner+outer records',
        encrypted_runtime_advantage='未据此主张',source='MODE_CERTIFICATE.json; BBR_MODEL_REVIEW.md',
        note='Generate the target-specific Q; no claim that mode and median have the same Q or that this bound is globally optimal.')
    current={c['case_id']:c for c in json.loads((HERE/'CURRENT_CONSTRUCTION_CERTIFICATES.json').read_text(encoding='utf-8'))}
    for key,c in current.items():
        add(id='C_'+key,family_zh='当前表中显式加法构造',function=key,domain=c['input_domain'],
            representation='single additive statistic with saved p_i and Q',
            evidence_level='已证明构造；穷举结构优势',analytic_construction='yes',
            finite_check='all inputs passed in v2',checked_inputs=c['verified_cases'],
            structural_baseline='direct dense LUT',baseline_records=c['full_domain_cases'],
            construction_records=c['logical_records'],metric='dense inner+outer records',
            encrypted_runtime_advantage='未据此主张',source='CURRENT_CONSTRUCTION_CERTIFICATES.json#'+key,
            note='No new search; see CD_SAVED_CERTIFICATE_VERIFICATION.json. Runtime and parameter claims require separate encrypted records.')
    for i,c in enumerate(snapshot['selected'],1):
        elementary='elementary' in c['family'].lower()
        note=c['note']
        if c['function']=='floor division':
            note+=' The legacy valid-domain catalogue has 64 numerator and 63 denominator entries (127 inner entries): total1192. The manuscript padded-domain convention retains64+64 inner entries: total1193. Do not silently mix these counts.'
        add(id=f'L_{i:02}',family_zh=c['family'],function=c['function'],domain=c['parameters'],
            representation=c['construction'],evidence_level='既有穷举记录：相对直接 LUT 的结构优势',
            analytic_construction='finite candidate construction; see source implementation',
            finite_check=('legacy finite-grid check with numerical oracle; not rerun in v2' if elementary else 'legacy exhaustive finite-domain check; not rerun in v2'),
            checked_inputs=c['exhaustive_cases'],structural_baseline='direct LUT over stated valid domain',
            baseline_records=c['direct_records'],construction_records=c['decomposed_records'],
            metric=snapshot['metric'],encrypted_runtime_advantage='未据此主张',
            source=f'FUNCTION_CATALOGUE_SOURCE_SELECTED.json#/selected/{i-1}',note=note)
    with (HERE/'FUNCTION_CATALOGUE.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(rows=len(rows),proved_families=10,current_certified_instances=len(current),
        imported_positive_instances=len(snapshot['selected']),new_grid_runs=0,new_timing_runs=0),indent=2))

if __name__=='__main__':main()
