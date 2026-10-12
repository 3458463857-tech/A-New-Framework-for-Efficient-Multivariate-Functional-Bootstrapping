"""Rebuild the catalogue from saved records only. No function/FHE experiment runs."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if (HERE.parent / "README_zh.md").exists() else HERE.parents[2]
PUBLIC_PATHS = json.loads((HERE / "release_path_map.json").read_text(encoding="utf-8")) if (HERE / "release_path_map.json").exists() else {}
EVIDENCE = HERE / "evidence"
SNAP = EVIDENCE / "current_summaries"
SNAP.mkdir(exist_ok=True)

SOURCES = {
    "ours_small.csv": "work/DCC_fair_comparison_v5/experiments_ours_capacity/ours/summary/results.csv",
    "ours_large.csv": "work/DCC_fair_comparison_v5/experiments_ours_multibit/ours/summary/results.csv",
    "bbr_small.csv": "work/DCC_fair_comparison_v5/experiments_bbr/summary/small_functions_attempt1/results.csv",
    "bbr_large.csv": "work/DCC_fair_comparison_v5/experiments_bbr/summary/functions_attempt1/results.csv",
    "refined_small.csv": "work/DCC_fair_comparison_v5/experiments_refined_small_functions/summary/timings.csv",
    "refined_large.csv": "work/DCC_submission_polish_v4/experiments_refined_functions/summary/timings.csv",
    "meta_small.csv": "work/DCC_fair_comparison_v5/experiments_meta_small/summary/results.csv",
    "meta_large.csv": "work/DCC_fair_comparison_v5/experiments_meta_extended/summary/results.csv",
    "division_r2.csv": "work/DCC_targeted_revision_v2/final_experiments/summary/timings.csv",
    "refined_division_extended.csv": "work/DCC_submission_polish_v4/experiments_refined_extended/summary/timings.csv",
    "meta_full8.csv": "work/DCC_revision_v3/experiments_meta/summary/protocol1_timings.csv",
    "bbr_division.json": "work/DCC_fair_comparison_v5/experiments_bbr/summary/division_pbs15x2_attempt1/results.json",
    "division_t8.json": "work/DCC_final_polish_v6/new_experiments/summary/results.json",
    "bbr_division_t8_t32.json": "work/DCC_final_polish_v6/new_experiments/bbr/summary/results.json",
    "definitions_large.py": "work/DCC_submission_polish_v4/experiments_functions/scripts/task_definitions.py",
    "definitions_small.py": "work/DCC_fair_comparison_v5/experiments_small_functions/scripts/task_definitions.py",
    "certificates_small.json": "work/DCC_fair_comparison_v5/experiments_small_functions/inputs/plaintext_certificates.json",
    "certificates_current.json": "work/DCC_fair_comparison_v5/experiments_ours_capacity/ours/summary/plaintext_certificates.json",
    "original_functions.py": "work/DCC_revision_2026-10-10_v1/original_code/A-New-Framework-for-Efficient-Multivariate-Functional-Bootstrapping-main/Section4_Code/chapter4_compression/functions.py",
    "original_compress.py": "work/DCC_revision_2026-10-10_v1/original_code/A-New-Framework-for-Efficient-Multivariate-Functional-Bootstrapping-main/Section4_Code/chapter4_compression/compress.py",
    "existing_family_notes.md": "work/DCC_targeted_revision_v2/evidence/FUNCTION_CATALOGUE.md",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

provenance = []
for name, source in SOURCES.items():
    p = ROOT / source
    if not p.exists() and source in PUBLIC_PATHS:
        p = ROOT / PUBLIC_PATHS[source]
    if p.exists():
        shutil.copyfile(p, SNAP / name)
    assert (SNAP / name).exists(), name
    provenance.append({"snapshot": f"evidence/current_summaries/{name}", "source_from_project_root": source, "public_package_path": PUBLIC_PATHS.get(source, f"functions/evidence/current_summaries/{name}"), "sha256": sha(SNAP / name)})

def readcsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def saved(name):
    return readcsv(SNAP / name)

def indexed(name, key="task_id"):
    return {r[key]: r for r in saved(name)}

original_path = EVIDENCE / "original_study/intermediate_routes/intermediate_routes.csv"
original = readcsv(original_path)
base = readcsv(EVIDENCE / "original_study/results/all_results.csv")
selected = [(i + 2, r) for i, r in enumerate(original) if r["retained"] == "True"]
assert len(selected) == 45
assert sum(r["section"] == "elementary" for _, r in selected) == 19

# Chinese names and exact definitions; z indices below are zero-based, as in the original note.
DEFS = {
 "floor division": ("整数商", r"$\lfloor m/d\rfloor$"),
 "3-input geometric mean": ("三输入几何均值取整", r"$\lfloor(x_1x_2x_3)^{1/3}\rfloor$"),
 "variable-index integer root": ("可变次数整数根", r"$\lfloor a^{1/b}\rfloor$"),
 "variable-base integer logarithm": ("可变底整数对数", r"$\lfloor\log_a b\rfloor$"),
 "floor(log(1+x)/log(1+y))": ("对数比取整", r"$\lfloor\log(1+x)/\log(1+y)\rfloor$"),
 "floor(log(1+x^2)/log(1+y^2))": ("平方后对数比取整", r"$\lfloor\log(1+x^2)/\log(1+y^2)\rfloor$"),
 "floor(sqrt(1+x^2)/sqrt(1+y^2))": ("平方根比取整", r"$\lfloor\sqrt{1+x^2}/\sqrt{1+y^2}\rfloor$"),
 "floor(asinh(x)/asinh(y))": ("反双曲正弦比取整", r"$\lfloor\operatorname{asinh}(x)/\operatorname{asinh}(y)\rfloor$"),
 "floor(sqrt(log(1+x)/log(1+y)))": ("对数比平方根取整", r"$\lfloor\sqrt{\log(1+x)/\log(1+y)}\rfloor$"),
 "floor(cuberoot(log(1+x)/log(1+y)))": ("对数比立方根取整", r"$\lfloor\sqrt[3]{\log(1+x)/\log(1+y)}\rfloor$"),
 "floor(sqrt(asinh(x)/asinh(y)))": ("反双曲正弦比平方根取整", r"$\lfloor\sqrt{\operatorname{asinh}(x)/\operatorname{asinh}(y)}\rfloor$"),
 "maximum": ("最大值", r"$z_5$"), "minimum": ("最小值", r"$z_0$"),
 "lower median": ("下中位数", r"$z_2$"), "upper median": ("上中位数", r"$z_3$"),
 "second smallest": ("第二小值", r"$z_1$"), "second largest": ("第二大值", r"$z_4$"),
 "range": ("极差", r"$z_5-z_0$"), "interquartile range": ("四分位距", r"$z_3-z_1$"),
 "top-two sum": ("最大两项和", r"$z_5+z_4$"), "bottom-two sum": ("最小两项和", r"$z_0+z_1$"),
 "top-three sum": ("最大三项和", r"$z_3+z_4+z_5$"), "central-four sum": ("中间四项和", r"$z_1+z_2+z_3+z_4$"),
 "median-pair gap": ("中间两项差", r"$z_3-z_2$"),
 "median absolute deviation": ("中位绝对偏差", r"$\operatorname{med}_{\rm low}(|x_i-z_2|)$"),
 "median-neighborhood count": ("中位数邻域计数", r"$\sum_i\mathbf1[|x_i-z_2|\le1]$"),
 "mode": ("众数（并列取最小）", r"$\min\arg\max_v c_v$"),
 "distinct count": ("不同符号数", r"$\sum_v\mathbf1[c_v>0]$"),
 "plurality margin": ("最高两频数差", r"$c_{[1]}-c_{[2]}$"),
 "modal frequency": ("众数频数", r"$\max_v c_v$"),
 "singleton-symbol count": ("恰出现一次的符号数", r"$\sum_v\mathbf1[c_v=1]$"),
 "repeated-symbol count": ("至少出现两次的符号数", r"$\sum_v\mathbf1[c_v\ge2]$"),
 "exact-two-symbol count": ("恰出现两次的符号数", r"$\sum_v\mathbf1[c_v=2]$"),
 "heavy-symbol count": ("至少出现三次的符号数", r"$\sum_v\mathbf1[c_v\ge3]$"),
 "least positive frequency": ("最小正频数", r"$\min\{c_v:c_v>0\}$"),
 "occupied-frequency range": ("非零频数极差", r"$\max_vc_v-\min\{c_v:c_v>0\}$"),
 "number of modal symbols": ("并列众数个数", r"$\sum_v\mathbf1[c_v=\max_uc_u]$"),
}

rows = []
for j, (line, r) in enumerate(selected, 1):
    name, formula = DEFS[r["function"]]
    matched = [b for b in base if b["function"] == r["function"] and b["parameters"] == r["parameters"]]
    rows.append({
        "catalog_id": f"O{j:02}", "record_group": "original_structural", "function_zh": name,
        "function_original": r["function"], "definition_tex": formula, "domain": r["parameters"],
        "evidence_level": "已有有限域明文验证；逻辑记录比较；非密文计时",
        "direct_records": r["direct_records"], "logical_records": r["our_records"],
        "record_convention": "原脚本按连续一元LUT区间逐次累计；非物理存储或密文时间",
        "abstract_lut_evaluations": r["our_lut_evals"], "output_cardinality": r["output_cardinality"],
        "scale_M": matched[0]["scale"] if matched else "", "verified_clear_inputs": r["exhaustive_cases"],
        "alternative_records": r["alternative_records"], "alternative_route": r["alternative_route"],
        "representation": r["paper_route"], "ours_mean_ms": "", "bbr_mean_ms": "", "refined_mean_ms": "", "meta_mean_ms": "", "native_mean_ms": "",
        "faster_than_tested_methods": "未在原定义域密文计时；商见T20，采用不同填充记账" if j == 1 else "原定义域无密文计时结论",
        "source": f"evidence/original_study/intermediate_routes/intermediate_routes.csv:{line}",
        "source_detail": "原PDF表1" if j <= 19 else "原PDF表2",
        "notes": "浮点/高精度有限检查不能推广为全实数域证明" if r["section"] == "elementary" else "比较网络或直方图复合，不统一称为单层加性表示",
    })

TASK_NAMES = {
    "hamming_interval10": ("汉明重量区间", 2, 10, r"$\mathbf1[4\le\sum_i x_i\le6]$"),
    "set_interval4_6": ("集合计数区间", 4, 6, r"$\mathbf1[2\le c_{\{1,3\}}\le4]$"),
    "set_threshold4_6": ("集合计数阈值", 4, 6, r"$\mathbf1[c_{\{0,2\}}\ge3]$"),
}
for family, label, formula in [
    ("lower_median", "下中位数", r"$x_{(\lfloor(n+1)/2\rfloor)}$"),
    ("mode", "众数（并列取最小）", r"$\min\arg\max_v c_v$"),
    ("max", "最大值", r"$x_{(n)}$"), ("range", "极差", r"$x_{(n)}-x_{(1)}$"),
    ("iqr", "四分位距", r"$x_{(\lfloor3(n-1)/4\rfloor+1)}-x_{(\lfloor(n-1)/4\rfloor+1)}$"),
    ("mad", "中位绝对偏差", r"$\operatorname{med}_{\rm low}(|x_i-\operatorname{med}_{\rm low}(x)|)$"),
    ("distinct", "不同符号数", r"$|\{x_1,\ldots,x_n\}|$"),
]:
    for n in ([4,6] if family in ("mode","iqr") else [3,6]):
        TASK_NAMES[f"{family}3_{n}"] = (label,3,n,formula)

order = ["hamming_interval10", "set_interval4_6", "set_threshold4_6", "lower_median3_3", "mode3_4", "max3_3", "range3_3", "iqr3_4", "mad3_3", "distinct3_3", "lower_median3_6", "mode3_6", "max3_6", "range3_6", "iqr3_6", "mad3_6", "distinct3_6"]
method_data = {}
method_sources = {}
for method in ["ours", "bbr", "refined", "meta"]:
    method_data[method] = {}
    method_sources[method] = {}
    for name in [f"{method}_large.csv", f"{method}_small.csv"]:
        for r in saved(name):
            method_data[method][r["task_id"]] = r
            method_sources[method][r["task_id"]] = name

for i, task in enumerate(order, 1):
    label,t,n,formula = TASK_NAMES[task]
    o = method_data["ours"][task]
    result = {
        "catalog_id": f"T{i:02}", "record_group": "current_encrypted", "function_zh": label,
        "function_original": task, "definition_tex": formula, "domain": f"[{t}]^{n}",
        "evidence_level": "全域明文表示验证；每个已测方法5次预热+30次密文计时均正确",
        "verified_clear_inputs": str(t**n), "direct_records": str(t**n),
        "logical_records": "", "record_convention": "本行只报告实际密文时间；不混入原结构记账",
        "abstract_lut_evaluations": "", "actual_ours_pbs": o["pbs_count"],
        "representation": "计数和+外表" if task.startswith("hamming") else "分组内表+和值+外表",
        "native_mean_ms": "", "source_detail": task,
        "notes": "参数与整体失败校准未统一；空白为未测，不是优势",
    }
    sources = []
    wins = []
    for method in ["ours", "bbr", "refined", "meta"]:
        d = method_data[method].get(task)
        result[f"{method}_mean_ms"] = d["mean_ms"] if d else ""
        if d:
            sources.append(f"{method}:evidence/current_summaries/{method_sources[method][task]}#{task}")
            if method != "ours" and float(o["mean_ms"]) < float(d["mean_ms"]):
                wins.append({"bbr":"BBR26","refined":"Refined-LHE","meta":"Meta-PBS"}[method])
    result["faster_than_tested_methods"] = ";".join(wins) or "本行未快于所测对照"
    result["source"] = " | ".join(sources)
    rows.append(result)

r2 = indexed("division_r2.csv", "run")
rd = indexed("refined_division_extended.csv", "t")
md16 = indexed("meta_full8.csv", "run")["protocol1_div16"]
bd16 = json.loads((SNAP / "bbr_division.json").read_text(encoding="utf-8-sig"))
new8 = {r['method']: r for r in json.loads((SNAP/'division_t8.json').read_text(encoding='utf-8'))}
newbbr = {r['t']: r for r in json.loads((SNAP/'bbr_division_t8_t32.json').read_text(encoding='utf-8'))}
for i,t in enumerate([16,32,64], 18):
    ours = r2[f"protocol1_dcc_div{t}"]
    native = r2[f"protocol1_native_div{t}"]
    refined = r2["protocol1_refined_div16"] if t == 16 else rd[str(t)]
    meta = md16 if t == 16 else method_data["meta"].get(f"division_t{t}")
    bbr = bd16 if t == 16 else None
    row = {"catalog_id": f"T{i:02}", "record_group": "current_encrypted_quotient", "function_zh": "整数商", "function_original": f"division_t{t}", "definition_tex": r"$\lfloor m/d\rfloor$", "domain": f"m=0..{t-1}; d=1..{t-1}", "evidence_level": "精确商定理及全域整数检查；已测配置5次预热+30次密文计时正确", "direct_records": str(t*(t-1)), "logical_records": str({16:205,32:501,64:1193}[t]), "record_convention":"现论文含d=0填充槽；与原合法域记账差1", "scale_M":str({16:22,32:44,64:89}[t]), "verified_clear_inputs":str(t*(t-1)), "actual_ours_pbs":str({16:42,32:114,64:205}[t]), "ours_mean_ms":ours["mean_ms"], "native_mean_ms":native["mean_ms"], "refined_mean_ms":refined["mean_ms"], "bbr_mean_ms":str(bbr["mean_ms"]) if bbr else "", "meta_mean_ms":meta["mean_ms"] if meta else "", "faster_than_tested_methods":"Native;BBR26" if t==16 else "本行未快于所测对照", "representation":"两对数内表+减法+商外表；不含余数乘减", "source":"evidence/current_summaries/division_r2.csv | evidence/current_summaries/refined_division_extended.csv | evidence/current_summaries/meta_full8.csv | evidence/current_summaries/meta_large.csv | evidence/current_summaries/bbr_division.json", "source_detail":f"division_t{t}", "notes":"BBR仅t16有修正PBS15/2成功实测，旧失败单列保留；Meta t64未测。"}
    if t == 32:
        assert meta, "Missing Meta t32 result"
        row['bbr_mean_ms'] = str(newbbr[32]['mean_ms'])
        row['faster_than_tested_methods'] = 'BBR26'
        row['source'] += ' | evidence/current_summaries/bbr_division_t8_t32.json'
    row['notes']='BBR t16/t32均为PBS15/2成功实测；t32为四个独立F17输入、两个F17输出；Meta t64未测。'
    rows.append(row)

row=dict(rows[62])
row.update(catalog_id='T21', function_original='division_t8', domain='m=0..7; d=1..7', direct_records='56', logical_records='205', record_convention='实测复用T16/M22电路的205项表示；不是t8专门压缩或优化结果', scale_M='22', verified_clear_inputs='56 (subset of verified T16 domain, 240 inputs)', actual_ours_pbs='42', source='evidence/current_summaries/division_t8.json | evidence/current_summaries/bbr_division_t8_t32.json',source_detail='division_t8', notes='本文沿用T16/M22电路；Native两radix块；Refined完整4位CBS和256项表；Meta8正半域打包m+8d。BBR修正PBS15/2，无新的失败率校准。')
for method in ['ours','native','refined','meta']:row[f'{method}_mean_ms']=str(new8[method]['mean_ms'])
row['bbr_mean_ms']=str(newbbr[8]['mean_ms'])
row['faster_than_tested_methods']='Native;BBR26'
rows.append(row)
assert len(rows) == 66
FAMILIES = [
    ("符号集合计数",r"$S=c_A$","symbol_count；indicator_representation", "返回计数本身"),
    ("阈值与多数表决",r"$Q(S)=\mathbf1[S\ge\tau]$","symbol_set_threshold；indicator_representation", "多数表决须指定偶数输入时的并列规则"),
    ("计数区间",r"$Q(S)=\mathbf1[a\le S\le b]$","symbol_set_interval；indicator_representation", "公开上下界0<=a<=b<=n"),
    ("精确计数谓词",r"$Q(S)=\mathbf1[S=k]$","exact_k；indicator_representation", "公开目标计数0<=k<=n"),
    ("计数奇偶",r"$Q(S)=S\bmod2$","indicator_representation + verify；填写Q", "已有统一计数构造适用；未声称现成专门密文命令"),
    ("计数余数",r"$Q(S)=S\bmod k$","indicator_representation + verify；填写Q", "k>=2；输出消息空间须容纳0..k-1，不同于只判余数为零"),
    ("多档、分桶或截断计数",r"$Q:\{0,\ldots,n\}\to Y$","indicator_representation + verify；填写Q", "公开有限输出表，输出范围Y须适配参数"),
    ("公开模板汉明球",r"$\mathbf1[\sum_i\mathbf1[x_i\ne a_i]\le r]$","hamming_ball；hamming_distance_representation", "公开模板a与公开半径0<=r<=n，非加密模板"),
]
for j,(label,formula,entry,note) in enumerate(FAMILIES,1):
    rows.append({"catalog_id":f"F{j:02}","record_group":"direct_construction_family","function_zh":label,"function_original":entry,"definition_tex":formula,"domain":"[t]^n; A subset [t]; public parameters (or public template a in [t]^n)","evidence_level":"直接构造可适用；沿用已记录计数表示，不代表新参数实验","direct_records":"t^n","logical_records":"at most nt+n+1","record_convention":"通用内表+外表；仿射内层可消去；只在nt+n+1<t^n时称此口径压缩","representation":"逐输入指示函数之和S，再查公开Q","faster_than_tested_methods":"本行无新增密文计时","source":"evidence/current_summaries/original_functions.py | evidence/current_summaries/original_compress.py | evidence/current_summaries/existing_family_notes.md","notes":note})
ORDER_EXAMPLES = dict(zip([r['function_original'] for r in rows[19:34]], [5,0,2,3,1,4,5,2,9,1,12,10,1,1,3]))
HIST_EXAMPLES = dict(zip([r['function_original'] for r in rows[34:45]], [0,5,1,3,3,2,1,1,1,2,1]))
for r in rows[:19]:
    name=r['function_original']
    if name=='floor division': a,b='m=7,d=2','3'
    elif name=='3-input geometric mean': a,b='(2,4,8)','4'
    elif name=='variable-index integer root': a,b='a=16,b=2','4'
    elif name=='variable-base integer logarithm': a,b='a=2,b=16','4'
    else:a,b='x=y=1','1'
    r['example_input'],r['example_output']=a,b
for r in rows[19:34]:r['example_input'],r['example_output']='(0,1,2,3,4,5)',str(ORDER_EXAMPLES[r['function_original']])
for r in rows[34:45]:r['example_input'],r['example_output']='(0,0,0,1,1,2,3,4)',str(HIST_EXAMPLES[r['function_original']])
small_examples=[('(1,1,1,1,1,0,0,0,0,0)',1),('(0,1,2,3,1,0)',1),('(0,1,2,3,1,0)',1),('(0,1,2)',1),('(0,0,1,1)',0),('(0,1,2)',2),('(0,1,2)',2),('(0,1,2,2)',2),('(0,0,2)',0),('(0,0,2)',2)]
for r,(a,b) in zip(rows[45:55],small_examples):r['example_input'],r['example_output']=a,str(b)
for r,b in zip(rows[55:62],[1,0,2,2,1,1,3]):r['example_input'],r['example_output']='(0,0,1,1,2,2)',str(b)
for r in rows[62:66]:r['example_input'],r['example_output']='m=7,d=2','3'
family_examples=[('S=5',5),('S=5,tau=4',1),('S=5,a=2,b=4',0),('S=5,k=5',1),('S=5',1),('S=5,k=3',2),('S=5,Q(S)=min(S,3)',3),('x=(0,0,0),template=(0,1,0),radius=1',1)]
for r,(a,b) in zip(rows[66:],family_examples):r['example_input'],r['example_output']=a,str(b)
fields = list(dict.fromkeys(k for r in rows for k in r))
with (HERE / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def fmt(value):
    return "--" if value in ("",None) else f"{float(value):.2f}"

def table(head, body, spec):
    return "\\begin{longtable}{"+spec+"}\n\\toprule\n"+head+r"\\"+"\n\\midrule\n\\endfirsthead\n\\toprule\n"+head+r"\\"+"\n\\midrule\n\\endhead\n"+"\n".join(body)+"\n\\bottomrule\n\\end{longtable}\n"

def measured_table(rs):
    body=[]
    for r in rs:
        domain=r["domain"]
        domain=re.sub(r"\[(\d+)\]\^(\d+)",r"$[\1]^{\2}$",domain)
        body.append(f'{r["catalog_id"]} {r["function_zh"]} & {domain} & '+" & ".join(fmt(r[f"{m}_mean_ms"]) for m in ["ours","bbr","refined","meta"])+r"\\")
    return table("函数 & 定义域 & 本文 & BBR26 & Refined & Meta",body,"@{}p{42mm}lrrrr@{}")

def elementary_domain(r):
    text=r["domain"]
    if r["function_original"]=="floor division":return r"$m=0{:}63,\ d=1{:}63$"
    if r["function_original"]=="3-input geometric mean":return r"$x_i=1{:}15$"
    if "a,b" in text:
        upper=16 if "16" in text else 32
        return f"$a,b=2:{upper}$"
    upper=31 if "t=32" in text else 63
    return f"$x,y=1:{upper}$"

doc = r'''\documentclass[UTF8,a4paper,10pt]{ctexart}
\usepackage[margin=20mm]{geometry}
\usepackage{amsmath,amssymb,booktabs,longtable,array,tabularx}
\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue]{hyperref}
\usepackage{xurl}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{适用函数与验证记录目录}\fancyhead[R]{2026-10-11}\fancyfoot[C]{\thepage}
\setlength{\headheight}{15pt}\setlength{\parindent}{2em}\setlength{\parskip}{3pt}
\setlength{\LTpre}{5pt}\setlength{\LTpost}{5pt}\renewcommand{\arraystretch}{1.12}
\title{适用函数与验证记录目录}
\author{论文及开源代码配套附件}\date{2026年10月11日}
\begin{document}
\maketitle
\noindent 本目录将原 \texttt{Application\_function.pdf} 的函数清单与后续验证、密文实测记录对应起来。
原附件中的45个结构实例全部保留，另列17个一般函数及4个整数商的当前密文比较，并给出已有计数构造可直接使用的8组变化。
同一函数在不同定义域上的行是不同参数实例，不代表新增函数类别。
本目录只整理保存记录；新近完成的 $t=8$ 除法及 BBR 的 $t=32$ 实测也列入，不增添理论结论。

\section{如何使用本目录}
寻找实现时，先选函数的\textbf{精确定义与输入域}，再看证据类型。
O01--O45 是原附件的有限域结构结果：比较的是连续一元查表区间的记录数，不能直接读成密文时延。
T01--T21 是已有密文实测：可比较所列设置下的均值，但参数、编码和整体失败概率尚未统一。
F01--F08 是直接构造可适用的函数族，不是新增实验实例。
\texttt{catalog.csv} 逐行保存定义、原始名称、数值类型、来源和对应记录；本文中的编号可直接检索该文件。

记 $[t]=\{0,\ldots,t-1\}$。单层表示为
\[
 f(x)=Q\!\left(\sum_i p_i(x_i)\right),\qquad E=\max_x\sum_i p_i(x_i)-\min_x\sum_i p_i(x_i).
\]
按论文的一般记账，直接表为 $t^n$ 项，表示为 $nt+E+1$ 项。
原附件的比较网络、直方图等多步方案则逐次累计所用一元表的连续区间；它们不能全部称作一个单层加性表示。
相同表重复使用、消去仿射内层和物理打包会改变实际实现成本，故两种记账不混为一列。

原附件表2中的 \texttt{Alt.} 是作者指定的代数、排序或直方图中间方案，\textbf{不是 BBR 的密文时间，也不是所有方案的最优成本}。
原脚本对这些替代方案中的密文乘法按零新增 LUT 记录处理。
本目录的结构表只列直接表与原方案；原 \texttt{Alt.} 数值和具体路线仍完整保存在 CSV 与证据目录中。
原投稿另有 BBR 满秩模型及异机校准投影，它们不纳入下列实测时间。

\section{直接构造可适用：计数之后改变输出表}
取 $p_i(x_i)=\mathbf1[x_i\in A]$，则 $S=\sum_i p_i(x_i)=c_A$。
已有的计数表示允许最后一步替换为公开的 $Q(S)$，因而同一组内表可用于下列函数。
这些是已有框架的具体用法，不需要为了每个阈值或区间重新搜索内表，也不将它们计为新的实验结果。
\begin{longtable}{@{}p{41mm}p{52mm}p{66mm}@{}}
\toprule
函数 & 输出表 & 现有代码入口\\
\midrule\endfirsthead
\toprule 函数 & 输出表 & 现有代码入口\\\midrule\endhead
F01 符号集合计数 & $Q(S)=S$ & \texttt{symbol\_count}\\
F02 阈值、多数表决 & $\mathbf1[S\ge\tau]$ & \texttt{symbol\_set\_threshold}；指定并列规则\\
F03 计数区间 & $\mathbf1[a\le S\le b]$ & \texttt{symbol\_set\_interval}\\
F04 精确计数 & $\mathbf1[S=k]$ & \texttt{exact\_k}\\
F05 计数奇偶 & $S\bmod2$ & 通用指示内表与验证程序；填写 $Q$\\
F06 计数余数 & $S\bmod k$，$k\ge2$ & 同上；区别于仅判断余数为零\\
F07 多档、分桶、截断 & 任意公开 $Q(0),\ldots,Q(n)$ & 同上；明确每一计数的输出\\
F08 公开模板汉明球 & $\mathbf1[\sum_i\mathbf1[x_i\ne a_i]\le r]$ & \texttt{hamming\_ball}、\texttt{hamming\_distance\_representation}\\
\bottomrule\end{longtable}
前七项要求 $x_i\in[t]$、公开 $A\subseteq[t]$；阈值和计数边界位于 $0,\ldots,n$。
F08 的模板 $a$ 与半径 $r$ 都是公开值。
例如 $S=5$ 时，阈值 $\tau=4$ 输出1，区间 $[2,4]$ 输出0，精确计数 $k=5$ 输出1；奇偶输出1，模3余数输出2，截断表 $Q(S)=\min(S,3)$ 输出3。
公开模板 $(0,1,0)$、输入 $(0,0,0)$ 的汉明距离为1，半径1的汉明球判定输出1。
按一般记账，内表与计数外表合计至多 $nt+n+1$ 项；只在它小于 $t^n$ 时据此称表项压缩。
改变输入数、字母表或输出档位后，密文程序仍需检查取值空间与噪声限制，本目录不对未测设置填写时间。

函数定义见 \path{evidence/current_summaries/original_functions.py}；
\path{original_compress.py} 中的 \path{indicator_representation} 构造指示内表，\texttt{verify} 接收具体目标函数并逐输入检查外表是否定义一致。
奇偶、余数和多档输出是该通用入口可表示的外表选择，尚未包装为本次独立密文计时任务。

\section{已有密文实测：从具体适用实例开始}
所有已完成配置均有5次预热、30次正式计时及逐输出解密检查。
计时从各输入已分别加密开始，到结果密文返回结束，包含服务端打包、转换、求值和恢复；不包含密钥生成、输入加密及离线构表。
均值单位为毫秒；空格记作 ``--''，不计为优势。标准差及逐次记录见源 summary。
BBR 使用作者求值器和相应函数的显式分解；Refined、Meta 使用作者程序及记录中的输入适配。

\subsection{小域统计与计数}
汉明区间判定为 $\mathbf1[4\le\sum_{i=1}^{10}x_i\le6]$。
集合区间判定为 $\mathbf1[2\le c_{\{1,3\}}\le4]$，集合阈值判定为 $\mathbf1[c_{\{0,2\}}\ge3]$，其中 $c_A=\#\{i:x_i\in A\}$。
按升序记 $x_{(1)}\le\cdots\le x_{(n)}$；下中位数取 $x_{(\lfloor(n+1)/2\rfloor)}$，众数并列取最小值。
四分位距取 $x_{(\lfloor3(n-1)/4\rfloor+1)}-x_{(\lfloor(n-1)/4\rfloor+1)}$，不插值；MAD 为各输入相对下中位数的绝对偏差的下中位数。
以下输入例子用于说明函数含义，不是新增实验数据：
\begin{longtable}{@{}p{42mm}p{70mm}p{45mm}@{}}
\toprule 函数 & 输入例子 & 输出与原因\\\midrule\endfirsthead
\toprule 函数 & 输入例子 & 输出与原因\\\midrule\endhead
T01 汉明区间 & 10个比特，其中5个为1 & 1，重量5在 $[4,6]$\\
T02 集合区间 & $(0,1,2,3,1,0)$ & 1，$\{1,3\}$ 中元素共3个\\
T03 集合阈值 & $(0,1,2,3,1,0)$ & 1，$\{0,2\}$ 中元素共3个\\
T04 下中位数 & $(0,1,2)$ & 1，排序后中间项\\
T05 众数 & $(0,0,1,1)$ & 0，并列时取小值\\
T06 最大值 & $(0,1,2)$ & 2\\
T07 极差 & $(0,1,2)$ & $2-0=2$\\
T08 四分位距 & $(0,1,2,2)$ & $x_{(3)}-x_{(1)}=2$\\
T09 MAD & $(0,0,2)$ & 0；中心0，偏差为 $(0,0,2)$\\
T10 不同符号数 & $(0,0,2)$ & 2，符号为0和2\\
\bottomrule\end{longtable}
''' + measured_table(rows[45:55]) + r'''
在这些设置中，本文分别有7、8、6个实例快于所测 BBR、Refined、Meta；逐行优势对象见 CSV。
例如三输入极差只快于 Refined、Meta，四输入众数与四分位距未显示优势。
这组统计不包括未测方法，也不扩展到其他定义域。

\subsection{同类函数扩大到六个三值输入}
下表保留同一批统计函数的较大域结果，定义与前节一致。
例如输入 $(0,0,1,1,2,2)$ 的下中位数、众数、最大值、极差、四分位距、MAD、不同符号数依次为 $1,0,2,2,1,1,3$。
此时四分位距为 $x_{(4)}-x_{(2)}$；MAD 的中心和偏差中位数都按下中位数取值。
''' + measured_table(rows[55:62]) + r'''
这些六输入实例仍然适用，表示检查及全部密文输出均正确；只是本文当前实现的 PBS 参数更大，在所测三个对照面前没有时延优势。
较小表项数与较快密文求值因此应分别判断；这里没有删除较大域记录。

\subsection{整数商}
定义为 $\lfloor m/d\rfloor$，其中 $0\le m<t$、$1\le d<t$，不包含余数所需的乘减。
例如 $m=7,d=2$ 时返回3。
$t=16,32,64$ 的当前表示按包含除数零填充槽的口径分别为205、501、1193项，尺度为22、44、89。
$t=8$ 实测直接复用 $T=16,M=22$ 电路，没有声称将表或 PBS 数优化到三位输入的最小值。
''' + table("$t$ & 本文 & 原生除法 & BBR26 & Refined & Meta", [str(t)+" & "+" & ".join(fmt(r[f"{m}_mean_ms"]) for m in ["ours","native","bbr","refined","meta"])+r"\\" for t,r in [(8,rows[65]),(16,rows[62]),(32,rows[63]),(64,rows[64])]], "@{}rrrrrr@{}") + r'''
$t=8,16$ 时本文快于所测原生除法和 BBR，但慢于 Refined 与 Meta；$t=32$ 时仅快于所测 BBR，$t=64$ 时未显示优势。
BBR 的三条成功商记录均使用 PBS 分解15/2，底层维数与加密噪声不变；旧失败和诊断记录另存，不沿用原参数表的失败率标签。$t=32$ 独立加密四个输入块并返回两个 $\mathbb Z_{17}$ 密文。
在 $t=8$ 行，Refined 保留两个完整4位 CBS 与256项表，Meta 使用8位负循环正半域并在线打包 $m+8d$；Native 保留两个 radix 块。
Meta 的 $t=16$ 使用完整域8位配置，$t=32$ 使用11位负循环表的正半域；$t=64$ 缺少对应现成参数，未测。较大域行仍保留供比较。
各方法完整参数及安全声明以论文参数附录和各程序记录为准，本目录不另行估算统一整体失败率。

\section{原附件保留的初等复合函数}
下表逐项对应原附件表1及原始 \texttt{intermediate\_routes.csv}。
``记录''是原方案逻辑表项总数，``调用''是原抽象一元 LUT 求值次数，\textbf{不是本机实测的 PBS 次数}。
除商的整数恒等式另有论文证明外，以下数值结论限定于原脚本已检查的有限域。
原脚本对超越比值函数的直接输出作80位、110位十进制精度交叉检查；这不是对任意参数或全实数域的符号证明。
记号 $a{:}b$ 表示从 $a$ 到 $b$ 的闭整数区间。
例子：三输入几何均值在 $(2,4,8)$ 返回4；可变次数整数根在 $(a,b)=(16,2)$ 返回4；可变底整数对数在 $(a,b)=(2,16)$ 返回4。后十四行的比值函数在 $x=y=1$ 时均返回1。
'''
body=[]
for r in rows[:19]:
    body.append(f'{r["catalog_id"]} {r["definition_tex"]} & {elementary_domain(r)} & {r["direct_records"]} & {r["logical_records"]} & {r["abstract_lut_evaluations"]}'+r'\\')
doc += table("函数 & 原检查域 & 直接表 & 记录 & 调用",body,"@{}p{72mm}p{33mm}rrr@{}")
doc += r'''
原 O01 按合法内层域 $64+63$ 计数为1192项；当前商表将除数零位置填充，按 $64+64$ 计数为1193项。
这一个槽位的差异是记账口径，不是不同的数学正确性结论或一次新的速度实验。
其余初等复合函数在所列原域没有本目录对应的密文计时，适合先复用保存的内外表与有限域检查，而不先声称加速。

\section{原附件保留的顺序统计与频数统计}
\subsection{六个八值输入的顺序统计}
本节定义域均为 $[8]^6$，直接表均为262144项。
沿用原附件的从零编号 $z_0\le\cdots\le z_5$。
比较网络中的小 LUT 组合给出以下原始记录；其原域未做对应密文实测，不能把前面的三值实例时间移到这里。
``例值''统一使用输入 $(0,1,2,3,4,5)$。
'''
body=[]
for r in rows[19:34]:
    body.append(f'{r["catalog_id"]} {r["function_zh"]} & {r["definition_tex"]} & {r["example_output"]} & {r["logical_records"]} & {r["abstract_lut_evaluations"]}'+r'\\')
doc += table("函数 & 精确定义 & 例值 & 记录 & 调用",body,"@{}p{53mm}p{59mm}rrr@{}")
doc += r'''
例如完整排序使用已保存的12比较器网络；极差和中间四项和使用7比较器的最大/最小值过程。
MAD 记录包含两次排序及六个绝对差值表。这里只给既有程序的构造，未宣称比较次数最优。

\subsection{八个五值输入的直方图统计}
本节定义域均为 $[5]^8$，直接表均为390625项。
令 $c_v=\#\{i:x_i=v\}$，$c_{[1]}\ge c_{[2]}$ 是包含零频数在内的最大两个频数。
原记账包括构造所有五个计数所需的200项，以及后续计数查表或比较。
``例值''统一使用输入 $(0,0,0,1,1,2,3,4)$，即 $(c_0,c_1,c_2,c_3,c_4)=(3,2,1,1,1)$。
'''
body=[]
for r in rows[34:45]:
    body.append(f'{r["catalog_id"]} {r["function_zh"]} & {r["definition_tex"]} & {r["example_output"]} & {r["logical_records"]} & {r["abstract_lut_evaluations"]}'+r'\\')
doc += table("函数 & 精确定义 & 例值 & 记录 & 调用",body,"@{}p{54mm}p{59mm}rrr@{}")
doc += r'''
这些行扩充了可复用的函数种类，但不证明任意输入数或字母表大小下仍压缩，也不证明它们都可改写成同一单层表示。
其他候选、限定比较中未保留的行及已有重复检查记录继续保存在原始证据文件中；本目录不根据它们额外增加适用性结论。

\section{文件与复用入口}
以下 \path{experiments/} 路径从公开包根目录开始；本附件及 \path{evidence/} 位于 \path{functions/}。完整步骤见 \path{docs/RUN_COMMANDS.md}，逐项结果见 \path{TABLE_INDEX.csv}。
原初等复合函数见 \path{evidence/original_study/run_experiments.py}；原比较网络与直方图统计见 \path{evidence/original_study/compare_intermediate_routes.py}。
当前程序在完整开源包的以下位置，各目录 README 给出依赖和运行命令（路径相对于项目根）：
\begin{itemize}
\item 本文小域与计数：\path{experiments/ours_small/ours/src/bin/functions_checked.rs}；六输入三值统计在\path{experiments/ours_large/ours/src/bin/functions_checked.rs}。
\item BBR：\path{experiments/bbr/source/HLUT-rs/src/bin/} 中的 \path{matched_functions.rs}、\path{matched_small_functions.rs}；修正商为 \path{matched_division_pbs15x2.rs}。
\item Refined：\path{experiments/refined_statistics/} 与 \path{experiments/refined_small/} 中 \path{source/refined-tfhe-lhe/benches/bench_functions.rs}。
\item Meta：\path{experiments/meta_statistics/source/META-FBS/cmd/dccextended/main.go} 及小域目录 \path{experiments/meta_small/source/META-FBS/cmd/dccsmall/main.go}。
\end{itemize}
\begin{itemize}
\item 新增商记录：\path{experiments/division_t8/source/} 为四路 $t=8$ 驱动，\path{experiments/bbr_division/source/} 为 BBR 的 $t=8,32$ 驱动；输入与逐次日志均在相邻目录。
\item \texttt{catalog.csv}：74行可检索索引，分为45个原结构实例、21个当前密文实例及8个直接构造族，部分函数和域重叠。
\item \texttt{evidence/Application\_function\_original.pdf} 及同名文本：用户压缩包内原附件的原样副本与提取文本。
\item \texttt{evidence/original\_study/}：原压缩包的 \texttt{Reproduction\_Materials\_for\_Application\_function/}，包含脚本、全部 CSV/JSON 及已有重复检查结果。
\item \texttt{evidence/current\_summaries/}：当前时间汇总与函数定义的副本；完整逐次日志和代码仍位于开源包中 \texttt{provenance.json} 指向的位置。
\item \texttt{rebuild\_catalog.py}：只读取保存的记录，重建本目录 CSV 和 \LaTeX 源；不执行函数枚举或密文实验。
\end{itemize}
原附件末页的旧目录名和“第3节代码暂未公开”不再作为当前说明：当前包已包含除法代码、修正运行及逐次记录。
正文保留核心定义和实测比较即可；本附件提供更多函数与旧结构结果的检索入口。
\end{document}
'''
(HERE / "function_catalog.tex").write_text(doc, encoding="utf-8")

provenance += [{"snapshot": str(p.relative_to(HERE)).replace("\\","/"), "sha256": sha(p)} for p in sorted((EVIDENCE / "original_study").rglob("*")) if p.is_file()]
provenance.append({"snapshot":"evidence/Application_function_original.pdf", "source_zip":"C:/Users/Wu/Desktop/代码压缩包.zip", "entry":"A-New-Framework-for-Efficient-Multivariate-Functional-Bootstrapping-main/Application_function.pdf", "sha256":sha(EVIDENCE / "Application_function_original.pdf")})
(HERE / "provenance.json").write_text(json.dumps({"operation":"record-only catalogue reconstruction; no new experiments", "sources":provenance},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
audit = {"original_retained_rows":45,"original_elementary":19,"original_order_statistics":15,"original_histogram_statistics":11,"encrypted_general_rows":17,"encrypted_quotient_rows":4,"direct_construction_families":8,"concrete_instances":66,"catalog_rows":len(rows),"numeric_ciphertext_means":sum(bool(r.get(f"{m}_mean_ms")) for r in rows for m in ["ours","bbr","refined","meta","native"]),"experimental_runs_performed":0,"latex_compiled":False}
assert audit["numeric_ciphertext_means"] == 84
for method, expected in [("BBR26",7),("Refined-LHE",8),("Meta-PBS",6)]:
    assert sum(method in r["faster_than_tested_methods"].split(";") for r in rows[45:55]) == expected
assert all(r["faster_than_tested_methods"] == "本行未快于所测对照" for r in rows[55:62])
(HERE / "catalog_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(audit,ensure_ascii=False))
