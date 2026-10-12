"""Link the four measured count predicates to catalogue families and raw runs."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V2=ROOT.parent
data=json.loads((ROOT/'summary/all_results.json').read_text())
runs={(r['method'],int(r['size']),r['predicate']):r for r in data['runs'] if r['run'].startswith('protocol1_')}
rows=[]
for n in (12,16):
    for predicate in ('threshold','interval'):
        ours=runs['count',n,predicate];other=runs['refined_count',n,predicate]
        assert ours['input_manifest_sha256']==other['input_manifest_sha256']
        definition=f'S >= {n//2}' if predicate=='threshold' else f'{n//3} <= S <= {2*n//3}'
        rows.append({'id':f'count_n{n}_{predicate}','n':n,'predicate':predicate,'definition':definition,
            'catalogue_family_id':'A_'+predicate,'catalogue_file':'evidence/FUNCTION_CATALOGUE.csv',
            'catalogue_csv_line':2 if predicate=='threshold' else 3,
            'dcc_mean_ms':ours['mean_ms'],'dcc_population_sd_ms':ours['population_sd_ms'],
            'refined_mean_ms':other['mean_ms'],'refined_population_sd_ms':other['population_sd_ms'],
            'observed_latency_ratio_refined_over_dcc':other['mean_ms']/ours['mean_ms'],
            'dcc_raw_log':'final_experiments/'+ours['raw_path'],'refined_raw_log':'final_experiments/'+other['raw_path'],
            'dcc_source_sha256':ours['source_sha256'],'refined_source_sha256':other['source_sha256'],
            'input_manifest_sha256':ours['input_manifest_sha256'],'measured_per_method':30,'warmups_per_method':5,
            'scope':'same-host direct Boolean-CBS full-LUT author route; different parameter/encoding configurations; no equal-certified-whole-circuit-failure claim'})
with (V2/'MEASURED_FUNCTIONS.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
text='''# 已完成的计数函数加密实测

最终统一协议已完成15个配置；本表仅列其中具有同机计数延迟优势的四个函数实例，分别对应适用目录的 `A_threshold` 和 `A_interval` 族。目录中的75项由函数族与不同证据等级的实例组成，不能说成75项都做了加密对照。其余实验（包括不利的除法结果）见 [最终完整汇总](final_experiments/summary/timings.csv)。

每种实现各5次预热、30次计时，使用相同边界与固定种子随机合法输入；CPU亲和均为0–7。两边都从分别新鲜加密的bit输入开始，作者路线所需Boolean CBS、GGSW/Fourier转换和完整LUT全部计时。我方使用checked求和和一次PBS。下列比率只是这两个具体配置的平均延迟比；参数与编码不同，尚未建立相同的经认证整体失败概率，也不把直接逐位作者路线当作Refined-LHE最优实现或下界。

时间单位：ms；±为总体标准差。S为输入bit之和。

| 实例 | 目录对应行 | 我方 | Refined逐位CBS+全LUT | Refined/我方 | 原始记录 |
|---|---|---:|---:|---:|---|
'''
for r in rows:
    text+=f"| n={r['n']}, {r['definition']} | [{r['catalogue_family_id']}（CSV行{r['catalogue_csv_line']}）]({r['catalogue_file']}#L{r['catalogue_csv_line']}) | {r['dcc_mean_ms']:.2f} ± {r['dcc_population_sd_ms']:.2f} | {r['refined_mean_ms']:.2f} ± {r['refined_population_sd_ms']:.2f} | {r['observed_latency_ratio_refined_over_dcc']:.3f} | [我方]({r['dcc_raw_log']}) / [Refined]({r['refined_raw_log']}) |\n"
text+='\n逐条输入输出、参数、计时范围与源码哈希见 [all_results.json](final_experiments/summary/all_results.json)；整体正确性证据等级见 [FAILURE_ANALYSIS](correctness_audit/FAILURE_ANALYSIS.md)。相应机器可读条目见 [MEASURED_FUNCTIONS.csv](MEASURED_FUNCTIONS.csv)。\n'
(V2/'MEASURED_FUNCTIONS.md').write_text(text,encoding='utf-8')
print('Linked four measured predicates to catalogue families and raw logs; no experiments run.')
