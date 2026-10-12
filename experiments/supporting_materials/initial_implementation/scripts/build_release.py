#!/usr/bin/env python3
"""Package readable code and every record, excluding compiler caches/runtime files."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={"build","__pycache__",".git","target"}

def category(path):
    p=path.as_posix()
    if p.startswith("results/"):return "revision_record_or_derived_summary"
    if "experiment_records/" in p or "/results/" in p or "/verification_rerun/" in p or "/intermediate_routes" in p:return "provided_historical_records"
    if p.startswith("third_party/"):return "upstream_baseline_source_and_license"
    if p.startswith("scripts/"):return "revision_script"
    if p.startswith("config/"):return "revision_configuration"
    if p.startswith("code/"):return "source_and_supplied_material"
    return "documentation"

def files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file()
        and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
        and p.suffix not in (".pyc",".zip")
        and p.name not in ("FILE_INDEX.csv","RELEASE_CONTENTS.json"))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():parser.error(f"refusing to replace existing release ZIP: {a.output}")
    items=[]
    for p in files():
        relative=p.relative_to(ROOT)
        items.append({"path":relative.as_posix(),"bytes":p.stat().st_size,
            "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"category":category(relative)})
    with (ROOT/"FILE_INDEX.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    metadata={"indexed_files":len(items),"uncompressed_bytes":sum(r["bytes"] for r in items),
        "excludes":sorted(EXCLUDED),"index_excludes_self_and_metadata":True,
        "private_review_material_included":False,"build_cache_included":False,
        "primary_historical_division_means_ms":[221.248942,593.430483,1226.251213],
        "primary_division_provenance":"author-confirmed supplied historical logs",
        "new_measurements":"results/revision_2026-10-10/encrypted_final/",
        "results_index":"docs/RECORD_INDEX.md"}
    (ROOT/"RELEASE_CONTENTS.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for row in items:z.write(ROOT/row["path"],"Reproducibility/"+row["path"])
        z.write(ROOT/"FILE_INDEX.csv","Reproducibility/FILE_INDEX.csv")
        z.write(ROOT/"RELEASE_CONTENTS.json","Reproducibility/RELEASE_CONTENTS.json")
    with zipfile.ZipFile(a.output) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert not any(set(Path(n).parts)&EXCLUDED for n in names)
        for row in items:
            assert hashlib.sha256(z.read("Reproducibility/"+row["path"])).hexdigest()==row["sha256"]
    print(json.dumps({"zip":str(a.output),"files":len(items)+2,"bytes":a.output.stat().st_size,
        "sha256":hashlib.sha256(a.output.read_bytes()).hexdigest(),"crc_and_all_file_hashes_verified":True}))

if __name__=="__main__":main()
