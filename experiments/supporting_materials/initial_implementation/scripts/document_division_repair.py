#!/usr/bin/env python3
"""Read existing logs and produce the additional repaired-circuit evidence."""
import difflib
import hashlib
import json
import math
from pathlib import Path
import statistics
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"results/revision_2026-10-10"

def records(p):
    return [dict(x.split("=",1) for x in line.split(",")[1:])
        for line in p.read_text().splitlines() if line.startswith("ENCRYPTED_RESULT,")]

def main():
    path=RUN/"division_checked_attempt2/division_checked64.log"
    destination=RUN/"division_checked_attempt2/summary.json"
    if destination.exists():raise SystemExit("refusing to replace repaired-circuit summary")
    revised=records(path);original=records(RUN/"encrypted_final/division64.log")
    assert len(revised)==len(original)==30
    assert [(r["m"],r["d"]) for r in revised]==[(r["m"],r["d"]) for r in original]
    assert all(r["expected"]==r["actual"] and r["pbs_count"]=="205" for r in revised)
    values=[float(r["elapsed_ms"]) for r in revised]
    source=ROOT/"code/Section3_Code/src/bin/algorithm1_noise_checked.rs"
    base=ROOT/"code/Section3_Code/src/bin/algorithm1_small_parameter.rs"
    summary={"t":64,"n":30,"warmups":0,"rayon_workers":8,"pbs_calls":205,
        "pbs_breakdown":{"input":86,"subtraction":17,"outer":102},
        "mean_ms":statistics.mean(values),"population_stddev_ms":statistics.pstdev(values),
        "median_ms":statistics.median(values),"min_ms":min(values),"max_ms":max(values),
        "parameter":"PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS",
        "same_ordered_input_pairs_as_unrepaired_additional_run":True,"all_observed_outputs_pass":True,
        "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "raw_log_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "calibrated_model_only_log2_union_estimate":math.log2(205)-64.442,
        "formal_end_to_end_tail_bound_proved":False,
        "role":"additional repaired variant; confirmed historical main table unchanged"}
    destination.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    diff="".join(difflib.unified_diff(base.read_text().splitlines(True),source.read_text().splitlines(True),
         fromfile="code/Section3_Code/src/bin/algorithm1_small_parameter.rs",
         tofile="code/Section3_Code/src/bin/algorithm1_noise_checked.rs"))
    (ROOT/"docs/division_noise_budget.patch").write_text(diff,encoding="utf-8")
    print(json.dumps(summary))

if __name__=="__main__":main()
