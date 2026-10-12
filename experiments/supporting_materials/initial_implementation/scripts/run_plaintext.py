#!/usr/bin/env python3
"""Run every retained public-input check and keep command/output metadata."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=None)
    a=p.parse_args()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out=(a.output_dir or ROOT/"results"/("plaintext_"+stamp)).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        p.error(f"refusing to overwrite nonempty output path: {out}")
    out.mkdir(parents=True,exist_ok=True)
    commands=[
      ("division16",ROOT/"code/Section3_Code",["reference/verify_algorithm1.py"]),
      ("division32",ROOT/"code/Section3_Code",["reference/verify_larger_domains.py","--t","32"]),
      ("division64",ROOT/"code/Section3_Code",["reference/verify_larger_domains.py","--t","64"]),
      ("representations",ROOT/"code/Section4_Code",["chapter4_compression/generate_table11_records.py","--output-dir",str(out/"representations")]),
      ("section4_tests",ROOT/"code/Section4_Code",["-m","unittest","discover","-s","tests","-v"]),
      ("catalogue",ROOT/"code/Section4_Code",["application_function_study/run_experiments.py","--output-dir",str(out/"catalogue")]),
      ("intermediate_routes",ROOT/"code/Section4_Code",["application_function_study/compare_intermediate_routes.py","--output-dir",str(out/"intermediate_routes")]),
      ("search_comparison",ROOT,["scripts/search_comparison.py","--output-dir",str(out/"search_comparison")]),
    ]
    env={"python":sys.version,"platform":platform.platform(),"machine":platform.machine(),
         "processor":platform.processor(),"logical_cpus":os.cpu_count(),"utc_start":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/"environment_python.json").write_text(json.dumps(env,indent=2)+"\n",encoding="utf-8")
    runs=[]
    for name,cwd,args in commands:
        command=[sys.executable,*args]
        started=time.perf_counter()
        with (out/(name+".log")).open("w",encoding="utf-8") as f:
            cp=subprocess.run(command,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,text=True)
        row={"name":name,"command":["python",*args],"cwd_relative":str(cwd.relative_to(ROOT)),
             "exit_code":cp.returncode,"elapsed_seconds":time.perf_counter()-started,"log":name+".log"}
        runs.append(row)
        print(json.dumps(row),flush=True)
        (out/"commands.json").write_text(json.dumps(runs,indent=2)+"\n",encoding="utf-8")
    return int(any(r["exit_code"] for r in runs))

if __name__=="__main__": raise SystemExit(main())
