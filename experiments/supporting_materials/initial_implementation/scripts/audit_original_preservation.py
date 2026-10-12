#!/usr/bin/env python3
"""Prove every supplied experiment record remains byte-identical in the release."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-source",type=Path,required=True)
    p.add_argument("--original-archive",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error("refusing to replace preservation audit")
    rows=[]
    for source in sorted(a.original_source.rglob("*")):
        if not source.is_file():continue
        rel=source.relative_to(a.original_source)
        target=ROOT/"code"/rel
        history=("experiment_records" in rel.parts or any(x in rel.parts for x in
            ("results","verification_rerun","intermediate_routes","intermediate_routes_verification_rerun","records")))
        exists=target.is_file()
        match=exists and digest(source)==digest(target)
        rows.append({"file":rel.as_posix(),"supplied_record":history,"present":exists,
            "unchanged":match,"original_sha256":digest(source),"revision_sha256":digest(target) if exists else None})
        assert exists,f"supplied file missing: {rel}"
        if history:assert match,f"supplied experiment record changed: {rel}"
    result={"all_supplied_files_present":True,"all_supplied_experiment_records_byte_identical":True,
        "supplied_file_count":len(rows),"supplied_experiment_record_count":sum(r["supplied_record"] for r in rows),
        "original_archive_sha256":digest(a.original_archive) if a.original_archive else None,
        "files":rows}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"PASS {len(rows)} supplied files present; {result['supplied_experiment_record_count']} supplied records byte-identical")
if __name__=="__main__":main()
