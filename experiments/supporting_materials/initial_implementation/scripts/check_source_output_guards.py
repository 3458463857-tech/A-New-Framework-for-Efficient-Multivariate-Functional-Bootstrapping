#!/usr/bin/env python3
"""Validate only CLI guards; do not invoke the expensive scientific routines."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"results/revision_2026-10-10/source_guard_checks"
SCRIPTS=["code/Section4_Code/chapter4_compression/generate_table11_records.py",
 "code/Section4_Code/application_function_study/run_experiments.py",
 "code/Section4_Code/application_function_study/compare_intermediate_routes.py",
 "code/Reproduction_Materials_for_Application_function/run_experiments.py",
 "code/Reproduction_Materials_for_Application_function/compare_intermediate_routes.py"]
def main():
    if DEST.exists():raise SystemExit("refusing to overwrite validation records")
    protected=ROOT/"results/revision_2026-10-10/representations"
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected.iterdir() if p.is_file()}
    rows=[]
    for relative in SCRIPTS:
        for args,expected in ((["--help"],0),(["--output-dir",str(protected)],2)):
            cmd=[sys.executable,str(ROOT/relative),*args]
            cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
            assert cp.returncode==expected,(relative,cp.returncode,cp.stdout)
            rows.append({"script":relative,"args":args,"exit":cp.returncode,"output":cp.stdout})
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected.iterdir() if p.is_file()}
    assert before==after
    DEST.mkdir()
    (DEST/"checks.json").write_text(json.dumps({"all_pass":True,"protected_representations_unchanged":True,"checks":rows},indent=2)+"\n",encoding="utf-8")
    print(f"PASS {len(rows)} source CLI guard checks; no experiment was executed")
if __name__=="__main__":main()
