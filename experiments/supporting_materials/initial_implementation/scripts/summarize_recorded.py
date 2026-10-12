#!/usr/bin/env python3
"""Create provenance-tagged tables directly from complete raw run logs."""
import argparse
import datetime
import csv
import json
from pathlib import Path
import re
import statistics
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/revision_2026-10-10"

def kv(line):
    return dict(s.split("=",1) for s in line.split(",") if "=" in s)

def main():
    global OUT
    p=argparse.ArgumentParser()
    p.add_argument("--run-dir",type=Path,default=OUT,help="read existing records; never modify them")
    p.add_argument("--output-dir",type=Path)
    a=p.parse_args()
    OUT=a.run_dir.resolve()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination=a.output_dir or ROOT/"results"/("summary_"+stamp)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        p.error(f"refusing to overwrite nonempty output path: {destination}")
    destination.mkdir(parents=True,exist_ok=True)
    rows=[]
    folders=[(OUT/"encrypted_attempt2","revision_diagnostic","concurrent_builds_possible"),
        (OUT/"encrypted_checked","revision_diagnostic","concurrent_builds_possible"),
        (OUT/"encrypted_final","revision_measured","serial_final")]
    for folder in sorted(OUT.glob("division_checked_attempt*")):
        folders.append((folder,"revision_measured" if (folder/"exit_codes.tsv").exists() and "run\t0" in (folder/"exit_codes.tsv").read_text() else "revision_diagnostic", "additional_noise_checked_variant"))
    for folder,label,role in folders:
        for path in sorted(folder.glob("*.log")):
            groups={}
            for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
                if line.startswith(("CHECKED_RESULT,","TABLE11_RESULT,")):
                    parts=line.split(",");case=parts[1]
                    groups.setdefault(case,[]).append(float(parts[-1]))
                elif line.startswith(("ENCRYPTED_RESULT,","BASELINE_RESULT,")):
                    data=kv(line)
                    groups.setdefault(path.stem,[]).append(float(data["elapsed_ms"]))
            for case,values in groups.items():
                rows.append({"source_class":label,"role":role,"case":case,"n":len(values),
                    "mean_ms":statistics.mean(values),"stddev_ms":statistics.pstdev(values),
                    "median_ms":statistics.median(values),"min_ms":min(values),"max_ms":max(values),
                    "raw_log":str(path.relative_to(ROOT)).replace("\\","/"),
                    "correctness":"every logged result output-checked; not a failure-probability proof"})
    historical=ROOT/"code/Section4_Code/experiment_records/run_20260810T052530Z/summary.json"
    for r in json.loads(historical.read_text())["table11"]:
        rows.append({"source_class":"provided_historical_log","role":"legacy_parameter_noise_budget_exceeded",
            "case":r["case_id"],"n":30,"mean_ms":r["average_online_ms"],"stddev_ms":r["stddev_ms"],
            "median_ms":r["median_ms"],"min_ms":r["minimum_ms"],"max_ms":r["maximum_ms"],
            "raw_log":str(historical.relative_to(ROOT)).replace("\\","/"),
            "correctness":"historical output checks; legacy aggregate failure probability uncalibrated"})
    for path in (ROOT/"code/Section3_Code/experiment_records/run_20260816_table10").glob("*.log"):
        data=[kv(l) for l in path.read_text().splitlines() if l.startswith("ENCRYPTED_RESULT,")]
        values=[float(r["elapsed_ms"]) for r in data]
        if values:
            rows.append({"source_class":"author_confirmed_historical_measurement","role":"corrected_primary_division_table",
                "case":path.stem,"n":len(values),"mean_ms":statistics.mean(values),"stddev_ms":statistics.pstdev(values),
                "median_ms":statistics.median(values),"min_ms":min(values),"max_ms":max(values),
                "raw_log":str(path.relative_to(ROOT)).replace("\\","/"),
                "correctness":"historical output checks; full circuit failure budget unresolved"})
    if rows:
        with (destination/"timing_provenance.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (destination/"timing_provenance.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    for r in rows:
        if r["role"] in ("serial_final","additional_noise_checked_variant"):print(json.dumps(r))

if __name__=="__main__":main()
