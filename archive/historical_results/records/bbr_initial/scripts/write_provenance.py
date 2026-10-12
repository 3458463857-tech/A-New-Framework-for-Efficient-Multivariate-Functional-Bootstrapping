from pathlib import Path
import json, hashlib, difflib, csv
root=Path(__file__).resolve().parents[1]
original=root.parents[1]/'DCC_revision_2026-10-10_v1/evidence/artifact-HLUT-TCHES-main'
author=root/'source/author'
changed=[]; diff=[]
for relative in ['bench/HLUT-rs/src/files.rs','bench/HLUT-rs/src/decomposition.rs']:
    before=(original/relative).read_text().splitlines(keepends=True)
    after=(author/relative).read_text().splitlines(keepends=True)
    diff.extend(difflib.unified_diff(before,after,fromfile='author/'+relative,tofile='patched/'+relative))
    changed.append(dict(path=relative,original_sha256=hashlib.sha256((original/relative).read_bytes()).hexdigest(),
                        patched_sha256=hashlib.sha256((author/relative).read_bytes()).hexdigest()))
(root/'evidence/author_adapter.patch').write_text(''.join(diff))
table=author/'parameters/optimizer_cjp_odd-128.csv'
rows=list(csv.DictReader(table.open()))
selected=[r for r in rows if r['p']=='17' and r['nu']=='5'][0]
provenance=dict(author_url='https://github.com/CryptoExperts/artifact-HLUT-TCHES',
    commit='088029cb4cd3a6b33ac10e0c78ea193b1835216d',changes=changed,
    new_files=['bench/HLUT-rs/src/bin/matched_tasks.rs'],count_parameter_row=selected,
    parameter_table_sha256=hashlib.sha256(table.read_bytes()).hexdigest(),
    compiler='rustc 1.96.0 release, author Cargo.lock --locked',
    count_interface_audit='../theory/BBR_COUNT_INTERFACE_REVIEW.md',
    failures=[
        {'attempt':'historical offline Cargo','outcome':'missing csv/clap cache; not an algorithmic failure'},
        {'attempt':'initial v3 author build','outcome':'successful 38.01 s; temporary /tmp executable disappeared on WSL restart; stdout/stderr retained'},
        {'attempt':'python3 -m venv /tmp/dcc_v3_bbr_venv','outcome':'failed: ensurepip unavailable'},
        {'attempt':'temporary get-pip','outcome':'failed: /tmp virtual environment no longer existed; pip_bootstrap.log retained'},
        {'attempt':'persistent --without-pip venv and get-pip','outcome':'succeeded; log retained'},
    ],
    timing_coordination='Meta finished all timed measurements before BBR began. Python pip installer PID2070 was SIGSTOP-paused during the four BBR count groups, then resumed by shell EXIT trap.')
(root/'evidence/PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Provenance and exact source delta saved')
