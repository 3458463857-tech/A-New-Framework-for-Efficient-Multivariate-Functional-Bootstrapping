"""Assemble the read-only history and final source/evidence release; no experiments."""
import csv,hashlib,io,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V2=ROOT.parent
WORKSPACE=V2.parents[1]
OUTPUT=WORKSPACE/'outputs/DCC_revision_round2_2026-10-10'
OUT=OUTPUT/'DCC_open_source_code_and_records_round2.zip'
PAYLOAD={}
SHA=lambda b:hashlib.sha256(b).hexdigest()

def add(name,raw):
    assert not name.startswith('/') and '..' not in Path(name).parts and name not in PAYLOAD,name
    PAYLOAD[name]=raw

def import_zip(path,prefix,expected=None):
    raw=path.read_bytes()
    if expected:assert SHA(raw)==expected,(str(path),'historical ZIP changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if not name.endswith('/'):add(prefix+'/'+name,z.read(name))
    return {'file':path.name,'sha256':SHA(raw),'archive_prefix':prefix}

def add_tree(path,prefix):
    for p in sorted(path.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(path)
        if any(part in ('build','target','.git','__pycache__') for part in rel.parts):continue
        if p.suffix in ('.exe','.dll','.so','.pyc'):continue
        add(prefix+'/'+rel.as_posix(),p.read_bytes())

def main():
    assert not OUT.exists(),f'Refusing to overwrite {OUT}'
    required=['FINAL_CIRCUIT_MANIFEST.md','NOISE_AUDIT.md','FAILURE_ANALYSIS.md']
    missing=[name for name in required if not (V2/'correctness_audit'/name).exists()]
    assert not missing,f'Wait for frozen technical reports: {missing}'
    imports=[]
    imports.append(import_zip(WORKSPACE/'outputs/reproducible_code_and_all_records_2026-10-10_v2.zip','history/v1',
        '856cb779b55549cf3728082fac65a5b439a2953d8255dc7fd97dfb075f4d7589'))
    imports.append(import_zip(WORKSPACE/'outputs/refined_lhe_targeted_comparison_source_and_records_2026-10-10_v2.zip','history/refined_pilot',
        'b5df328ad9724e18288fe8881c28a179c5f9eb0a1533f1b79a8d39a57988a2d8'))
    add_tree(ROOT,'final_experiments')
    add_tree(V2/'correctness_audit','correctness_audit')
    prefixes=('FUNCTION_CATALOGUE','BBR_FIXED_FUNCTION','BBR_MODEL_REVIEW','CURRENT_','MODE_','CD_')
    names={'build_function_catalogue.py','verify_saved_cd_certificates.py','verify_bbr_mode.py','refined_index_check.md','PUBLISHED_PERFORMANCE_EVIDENCE.md','published_performance.csv','source_manifest.json'}
    for p in sorted((V2/'evidence').iterdir()):
        if p.is_file() and (p.name.startswith(prefixes) or p.name in names):add('evidence/'+p.name,p.read_bytes())
    add_tree(V2/'03_Evidence/nested_equality_certificate','03_Evidence/nested_equality_certificate')
    p=V2/'03_Evidence/verify_nested.py';add('03_Evidence/verify_nested.py',p.read_bytes())
    p=V2/'03_Evidence/CORRECTNESS_AUDIT_INDEX.md';add('03_Evidence/CORRECTNESS_AUDIT_INDEX.md',p.read_bytes())
    for name in ('MEASURED_FUNCTIONS.md','MEASURED_FUNCTIONS.csv'):add(name,(V2/name).read_bytes())
    readme='''# DCC round 2 — code and complete experimental records

本包合并历史、初次作者基线试跑、最终统一协议、全域预算审计与构造证书。没有覆盖或删除旧记录；没有把历史时间、理论模型和最终实测混成一行。

请先看 `final_experiments/README.md` 与 `final_experiments/EXPERIMENT_INDEX.csv`。最终 15 个配置共 450 次计时与 75 次预热均通过输出检查；均值、总体标准差和全部输入输出见 `final_experiments/summary/`。这不证明极小密码失败率。全域消息/噪声预算和条件性失败概率说明见 `correctness_audit/`，其证据等级必须一并引用。

The current measurements use five warmups, thirty timed trials, a common boundary-plus-fixed-seed workload and eight logical CPUs. The measured count-family advantages apply to the disclosed direct Boolean-CBS author route; they do not establish a lower bound on Refined-LHE. Refined-LHE is faster on the measured t=16 division. DCC is faster than the matched native control at t=16 but slower at t=32 and t=64. All results, including unfavorable ones, remain in the archive.

## Directory map

| Path | Evidence class and purpose |
|---|---|
| `history/v1/Reproducibility/` | Byte-preserved earlier reproducibility distribution: supplied originals, historical experiment data, original failures, v1 reruns, searches, and the repaired t=64 attempt. Original nested paths are retained. |
| `history/refined_pilot/refined_lhe_targeted_comparison/` | Byte-preserved first Refined-LHE complete-path pilot (132.45 ms); enumeration-prefix sampling and unequal comparison warmups mean it is not a final-protocol row. |
| `final_experiments/` | Current exact source, lockfiles, fixed input manifests, commands, environments, all raw logs, measured summaries, source/data hashes and paper-table generators. |
| `correctness_audit/` | Final circuit manifests, whole-domain message/noise audits, conditional failure analysis, automated checks and their saved results. |
| `evidence/` | Positive function catalogue, corrected general-construction model, actual fixed-function decompositions, mode/current-construction certificates and verifiers. |
| `03_Evidence/nested_equality_certificate/` | Saved nested-equality certificate; verifier is `03_Evidence/verify_nested.py`. |

## Reproduction and licensing

Use each layer's README and commands. Current measurements can be reproduced from `final_experiments/README.md`; do not run heavy suites concurrently. The runners refuse an existing run directory. Repeated new measurements can differ because timing and fresh cryptographic randomness are not deterministic. Public input samples and plaintext certificates are deterministic.

Original author licenses remain beside their source. Refined-LHE is distributed with its author's MIT license. No blanket new license has been invented for the manuscript authors' own source or for third-party material; review the preserved notices before public release. No credentials, secret keys, build products, font files or dependency caches are included. External dependencies are pinned by lockfiles, not bundled as an entire environment.

`MANIFEST_SHA256.txt` hashes every distributed file except itself. `BUNDLE_INDEX.json` identifies imported history ZIPs and the final data/source index. The ZIP was checked for CRC integrity and against every listed file hash after construction.
'''
    add('README_先看这个.md',readme.encode())
    add('INDEX.md',('''# Evidence index

- Final performance rows: `final_experiments/summary/timings.csv`.
- All 525 outputs, parameters, hashes, sampling and timing scopes: `final_experiments/summary/all_results.json`.
- Source/data/run mapping: `final_experiments/EXPERIMENT_INDEX.csv`.
- Source snapshot and unchanged-author-code audit: `final_experiments/provenance/source_binding_audit.json`.
- Final circuit and probability basis: `correctness_audit/FINAL_CIRCUIT_MANIFEST.md`, `NOISE_AUDIT.md`, `FAILURE_ANALYSIS.md`.
- Structural function catalogue: `evidence/FUNCTION_CATALOGUE.md` and `.csv`; representation success is separate from measured encrypted speed.
- Four measured count-family comparisons with observed ratios and catalogue-row/raw-log links: `MEASURED_FUNCTIONS.md` and `.csv`.
- Mode result 61 records and historical 127: `evidence/MODE_CERTIFICATE.json`, `MODE_ALL_729.csv`, `MODE_HISTORY.json`.
- Fixed-function [3] evidence: `evidence/BBR_FIXED_FUNCTION_CERTIFICATES.json`, `BBR_MODEL_REVIEW.md`, `verify_saved_cd_certificates.py`.
- Nested construction: `03_Evidence/nested_equality_certificate/summary.json`, `03_Evidence/verify_nested.py`.
- User-confirmed historical division times and all previous failures/reruns: `history/v1/Reproducibility/` (follow its README and record index).
- Initial complete-path Refined-LHE pilot, before matched sampling: `history/refined_pilot/`.

No historical row should be attributed to the current protocol, and no conditional calibration estimate should be attributed to empirical error counts.
''').encode())
    index={'history_imports':imports,'final_data':'final_experiments/summary/all_results.json',
           'final_run_index':'final_experiments/EXPERIMENT_INDEX.csv','final_source_audit':'final_experiments/provenance/source_binding_audit.json',
           'source_and_data_hashes':'MANIFEST_SHA256.txt','no_build_caches':True}
    add('BUNDLE_INDEX.json',(json.dumps(index,indent=2)+'\n').encode())
    manifest=''.join(f'{SHA(raw)}  {name}\n' for name,raw in sorted(PAYLOAD.items()))
    add('MANIFEST_SHA256.txt',manifest.encode())
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUT,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(PAYLOAD.items()):z.writestr(name,raw)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(PAYLOAD)
        for name,raw in PAYLOAD.items():assert SHA(z.read(name))==SHA(raw),name
    report={'path':str(OUT),'files':len(PAYLOAD),'bytes':OUT.stat().st_size,'sha256':SHA(OUT.read_bytes()),'crc':'PASS','every_file_hash':'PASS'}
    (OUTPUT/'DCC_open_source_code_and_records_round2.sha256').write_text(report['sha256']+'  '+OUT.name+'\n',encoding='utf-8')
    (OUTPUT/'CODE_ARCHIVE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
