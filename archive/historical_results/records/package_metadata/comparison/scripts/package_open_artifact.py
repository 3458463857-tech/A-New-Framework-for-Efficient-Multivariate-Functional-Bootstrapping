"""Create the v3 source/records-only release, preserving round-2 entry bytes."""
from pathlib import Path, PurePosixPath
import csv, hashlib, json, os, shutil, statistics, zipfile

V3=Path(__file__).resolve().parent
WORK=V3.parent
PROJECT=WORK.parent
OUT=V3/'open_artifact'
RELEASE=PROJECT/'outputs/DCC_final_revision_2026-10-10'
OLD=PROJECT/'outputs/DCC_revision_round2_2026-10-10/DCC_open_source_code_and_records_round2.zip'
OLD_SHA='4dbc912c57eac2273b58a21e4b62fce299c39b2bcb6e2dd830cbcc750b57c189'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,text):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
assert not OUT.exists(), 'Refusing existing artifact staging directory'
assert sha(OLD)==OLD_SHA
OUT.mkdir(parents=True)
old_records=[]
with zipfile.ZipFile(OLD) as z:
    assert z.testzip() is None
    for entry in z.infolist():
        rel=PurePosixPath(entry.filename)
        assert not rel.is_absolute() and '..' not in rel.parts
        if entry.is_dir():continue
        content=z.read(entry)
        dest=OUT/'history/round2_release'/str(rel)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
        old_records.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(content).hexdigest()))

bbr=V3/'experiments_bbr'
bbr_index=json.loads((bbr/'ARCHIVE_FILE_INDEX.json').read_text())
for item in bbr_index['files']:
    p=bbr/item['path'];assert sha(p)==item['sha256']
    copy(p,OUT/'experiments_bbr'/item['path'])
for name in ['ARCHIVE_FILE_INDEX.json','MANIFEST_SHA256.txt']:
    copy(bbr/name,OUT/'experiments_bbr'/name)

skip_dirs={'.git','__pycache__','.pytest_cache','target','cache','gocache','toolchain','build','.build','.venv'}
skip_suffix={'.pyc','.pyo','.so','.exe','.dll','.pdb'}
def copy_tree(source,destination):
    for dirname,dirs,names in os.walk(source):
        dirs[:]=[d for d in dirs if d not in skip_dirs]
        for name in names:
            p=Path(dirname)/name
            if p.suffix in skip_suffix:continue
            copy(p,destination/p.relative_to(source))
meta=V3/'experiments_meta'
for name in ['inputs','provenance','results','scripts','source','summary']:
    copy_tree(meta/name,OUT/'experiments_meta'/name)
copy(meta/'README.md',OUT/'experiments_meta/README.md')
copy_tree(V3/'theory',OUT/'theory')

r2base=OUT/'history/round2_release/final_experiments'
r2=json.loads((r2base/'summary/all_results.json').read_text())['runs']
bbr_rows=json.loads((OUT/'experiments_bbr/summary.json').read_text())
meta_rows=json.loads((OUT/'experiments_meta/summary/protocol1_summary.json').read_text())
methods=['ours','bbr26','refined_lhe','meta_pbs','native_division']
rows=[];configs=[]
for task,size,predicate in [('division',16,'none'),('division',32,'none'),('division',64,'none')]+[('count',n,p) for n in (12,16) for p in ('threshold','interval')]:
    target=(f'floor(m/d), 0<=m<{size}, 1<=d<{size}' if task=='division' else
            (f'sum(x)>={size//2}, x in {{0,1}}^{size}' if predicate=='threshold' else f'{size//3}<=sum(x)<={2*size//3}, x in {{0,1}}^{size}'))
    row=dict(task=task,size=size,predicate=predicate,target=target,warmups_per_configuration=5,
        measured_per_configuration=30,statistic='mean and population SD, milliseconds',
        cpu_budget='same host; logical CPUs 0-7; budget8; actual parallelism differs',
        comparison_scope='same plaintext task/corpus; backend encodings and whole-path failure probabilities not numerically matched')
    expected_hash=None
    for method in methods:
        record=None; prefix=None
        if method in ('ours','native_division','refined_lhe'):
            key={'ours':('dcc' if task=='division' else 'count'),
                 'native_division':'native',
                 'refined_lhe':('refined_div' if task=='division' else 'refined_count')}[method]
            found=[r for r in r2 if r['method']==key and int(r['size'])==size and r['predicate']==predicate]
            if found:
                r=found[0];prefix='history/round2_release/final_experiments/'
                record=dict(mean_ms=r['mean_ms'],population_sd_ms=r['population_sd_ms'],median_ms=r['median_ms'],
                    raw=prefix+r['raw_path'].replace('\\','/'),source_sha256=r['source_sha256'],
                    input_sha256=r['input_manifest_sha256'],raw_sha256=r['raw_log_sha256'],
                    parameter=r['parameters']['name'])
        elif method=='bbr26' and task=='count':
            r=next(r for r in bbr_rows if r['n_or_t']==size and r['task']=='count-'+predicate)
            record=dict(mean_ms=r['mean_ms'],population_sd_ms=r['population_sd_ms'],median_ms=r['median_ms'],
                raw='experiments_bbr/'+r['raw'],source_sha256=r['source_sha256'],
                input_sha256=r['input_sha256'],raw_sha256=r['raw_sha256'],parameter='author p17,nu5,optimizer_cjp_odd-128; patched lookup filter')
        elif method=='meta_pbs':
            found=[r for r in meta_rows if int(r['size'])==size and r['predicate']==predicate and r['task']==('div' if task=='division' else 'count')]
            if found:
                r=found[0];raw='experiments_meta/'+r['log'].replace('\\','/')
                record=dict(mean_ms=r['mean_ms'],population_sd_ms=r['population_sd_ms'],median_ms=r['median_ms'],
                    raw=raw,source_sha256=r['adapter_sha256'],input_sha256=r['input_sha256'],
                    raw_sha256=sha(OUT/raw),parameter=r['parameter_set'])
        row[method+'_status']='measured' if record else ('target_decomposition_not_obtained_within300s' if method=='bbr26' and size==16 and task=='division' else 'not_measured')
        for field in ('mean_ms','population_sd_ms','median_ms','parameter','raw','raw_sha256','source_sha256'):
            row[method+'_'+field]=record[field] if record else ''
        if record:
            assert sha(OUT/record['raw'])==record['raw_sha256']
            if expected_hash is None:expected_hash=record['input_sha256']
            assert record['input_sha256']==expected_hash,(task,size,method)
            configs.append(dict(task=task,size=size,predicate=predicate,method=method,**record))
    row['input_manifest_sha256']=expected_hash
    measured=[m for m in methods if row[m+'_status']=='measured']
    row['fastest_among_measured_columns']=min(measured,key=lambda m:row[m+'_mean_ms'])
    rows.append(row)
assert len(rows)==7 and len(configs)==24
with (OUT/'CURRENT_MEASURED_FUNCTIONS.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
save(OUT/'CURRENT_MEASURED_CONFIGURATIONS.json',json.dumps(configs,indent=2)+'\n')
table=['# Current measured common tasks','', 'Milliseconds, mean ± population SD; five warmups + thirty timed evaluations per configuration.', '',
       '| Task | Ours | BBR26 | Refined-LHE | Meta-PBS | Native division | Fastest measured |',
       '|---|---:|---:|---:|---:|---:|---|']
for r in rows:
    cells=[f"{r[m+'_mean_ms']:.2f} ± {r[m+'_population_sd_ms']:.2f}" if r[m+'_status']=='measured' else '—' for m in methods]
    name=f"quotient t={r['size']}" if r['task']=='division' else f"count n={r['size']}, {r['predicate']}"
    table.append('| '+name+' | '+' | '.join(cells)+' | '+r['fastest_among_measured_columns']+' |')
table+=['', 'The CSV retains unrounded statistics, parameter labels, per-run links, hashes and missing-measurement reasons. BBR is fastest in the four count tasks. Refined-LHE is fastest at t=16; native division is fastest among the measured t=32/64 columns. These are comparisons of the named implementations, not claims of universal acceleration.', '',
    'BBR t=16 quotient: one fixed-seed 300-second author decomposition search did not yield the target certificate. No homomorphic time is substituted. Other empty cells were not measured. Counting routes differ: ours, BBR and Meta exploit the count statistic; Refined-LHE is the measured direct Boolean-selector/full-truth-table route. Cryptographic encodings and whole-path failure probabilities are not numerically matched.','']
save(OUT/'CURRENT_MEASURED_FUNCTIONS.md','\n'.join(table))

save(OUT/'README.md','''# DCC 可复现代码与全部实验记录 — 第三版

先看 [当前横向实测表](CURRENT_MEASURED_FUNCTIONS.md)；机器可读版本为
[CURRENT_MEASURED_FUNCTIONS.csv](CURRENT_MEASURED_FUNCTIONS.csv)。它覆盖 **7 个共同任务、24 个实测配置**，每组 5 次预热、30 次计时，统计为均值与总体标准差。所有列链接到原始日志并带源文件、输入和记录哈希。

四个计数任务中 BBR 最快；t=16 商的已测实现中 Refined-LHE 最快；t=32、64 的已测列中原生除法最快。本文在若干指定比较中较快，并不意味着所有适用函数都加速。旧目录的函数目录、证书数量或适用性列表不能当作实测加速数量。

## 当前数据入口

- [BBR 作者求值器：源码、四组实测与全部诊断](experiments_bbr/README.md)。计数使用显式 F17 分解。t=16 商的一次 300 秒作者搜索没有产生目标证书；这不是不适用结论，亦没有虚构同态时间。
- [Meta-PBS：源码及五组完整路径实测](experiments_meta/README.md)。商包括在线打包，计数包括在线求和；两者均包括完整域查表和符号消除。计数采用统计量适配，不是直接展开 12/16 位真值表。
- [第二版最终协议、本文/原生/Refined 源码及十五组记录](history/round2_release/final_experiments/README.md)。本版沿用这些有效结果，没有重新挑选或覆盖。
- [实现正确性与噪声预算审计](history/round2_release/correctness_audit/)、[第三版理论验证脚本、证书与审查](theory/README.md)。不同后端的编码与整体失败概率未数值对齐；局部参数标签不能直接当作完整任务保证。

## 历史记录

`history/round2_release/` 完整保留原第二版开源包的 680 个文件、内部路径与字节，包含 v1 原始/修复记录、首次 Refined pilot、第二版最终实验和全部失败尝试。其旧 README/表格只反映当时的比较；**当前总览以根目录 CURRENT_MEASURED_FUNCTIONS 为准**。历史旧主表数据、近期重测、模型估计和明文证书保持各自标签，不能互相替换。

## 验证与复现

仅核对交付文件，不运行密码实验：

```sh
python3 scripts/verify_bundle.py
```

各实现的运行命令、锁定依赖、参数、CPU 预算、输入、逐次输出及失败记录见相应 README。运行时编译目录、工具链、缓存与密钥不在本包中。新运行应使用新标签/新输出目录，不能覆盖已发布日志。所有计时来自同一机器、相同八个逻辑 CPU 预算，实际并行程度按实现披露。

`MANIFEST_SHA256.txt` 和 `MANIFEST.json` 列出除这两个清单自身之外的每个文件。外部 ZIP SHA256 和验证报告保护整个归档；清单不递归记录自身。`PROVENANCE.json` 保留输入包指纹与导入检查结果。

## 源码与许可范围

原作者许可证、依赖许可、固定提交号与补丁说明随源码保留。本包不新设统一许可证，也不把第三方许可扩大适用到论文自有代码。私人的 PKC 原论文、评审原文和用户提示文件没有纳入此代码记录包。
''')

verify='''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
expected={x['path'] for x in data['files']}
actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in ('MANIFEST.json','MANIFEST_SHA256.txt') and '__pycache__' not in p.parts}
assert actual==expected,(actual-expected,expected-actual)
for item in data['files']:
 p=root/item['path']
 assert p.stat().st_size==item['bytes'],item['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],item['path']
print('PASS:',len(expected),'file hashes; no experiment executed')
'''
save(OUT/'scripts/verify_bundle.py',verify)
copy(Path(__file__),OUT/'scripts/package_open_artifact.py')
provenance=dict(release='v3 source and records only',original_round2_archive_sha256=OLD_SHA,
    original_round2_entry_count=len(old_records),round2_import='byte-identical complete archive under history/round2_release',
    bbr_allowlist_sha256=sha(bbr/'ARCHIVE_FILE_INDEX.json'),bbr_allowlist_entries=len(bbr_index['files']),
    measured_common_tasks=len(rows),measured_configurations=len(configs),
    root_csv='CURRENT_MEASURED_FUNCTIONS.csv',author_licenses='preserved at source paths; no new umbrella license',
    exclusions='private paper/reviews/prompts; build/cache/toolchain/git directories; runtime compiled artifacts and keys',
    imported_round2_entries=old_records)
save(OUT/'PROVENANCE.json',json.dumps(provenance,indent=2)+'\n')

entries=[]
for p in sorted(OUT.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(OUT).as_posix()
    assert not any(x in p.parts for x in ('.git','.venv','.build','target','toolchain','build','__pycache__'))
    assert not any(w in rel.lower() for w in ('pkc审稿','prompt (2)','论文.zip','complete_revision_round2_private'))
    entries.append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p)))
save(OUT/'MANIFEST.json',json.dumps(dict(files=entries,file_count=len(entries),payload_bytes=sum(x['bytes'] for x in entries)),indent=2)+'\n')
save(OUT/'MANIFEST_SHA256.txt','\n'.join(f"{x['sha256']}  {x['path']}" for x in entries)+'\n')
RELEASE.mkdir(parents=True,exist_ok=True)
archive=RELEASE/'DCC_code_and_records_v3.zip'
assert not archive.exists(), 'Refusing existing final archive'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for x in entries:
        content=z.read(x['path'])
        assert len(content)==x['bytes'] and hashlib.sha256(content).hexdigest()==x['sha256']
    assert len(z.infolist())==len(entries)+2
    for x in old_records:
        assert hashlib.sha256(z.read('history/round2_release/'+x['path'])).hexdigest()==x['sha256']
assert sha(OLD)==OLD_SHA
report=dict(archive=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),
    zip_entries=len(entries)+2,manifest_payload_files=len(entries),zip_crc='PASS',all_payload_sha256='PASS',
    original_round2_entries_preserved=len(old_records),original_round2_archive_unchanged='PASS',
    bbr_allowlist_entries=len(bbr_index['files']),common_tasks=len(rows),measured_configurations=len(configs))
save(RELEASE/'DCC_code_and_records_v3.sha256',report['sha256']+'  '+archive.name+'\n')
save(RELEASE/'CODE_ARCHIVE_VERIFICATION_V3.json',json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
