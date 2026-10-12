"""Read-only analysis of retained diagnostics; writes a new evidence directory."""
import csv, difflib, hashlib, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "division_root_cause_attempt1"
OUT.mkdir(exist_ok=False)
Q = 2**64

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows(name):
    p = ROOT / "results" / name / "stages.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()], p

old, old_path = rows("division_diagnostic_attempt1")
new, new_path = rows("division_diagnostic_pbs15x2_attempt1")
by_stage = {r.get("stage"): r for r in old}
source = ROOT / "results/division_search_fixed_attempt1/search/decomposition/new_phis_17_2"
text = source.read_text().splitlines()
first = next(r for r in old if r.get("correct") is False)
assert first["stage"] == "atom.5.weighted_input"
alpha = list(map(int, text[text.index("5:") + 1].split()))
prev = [by_stage[s] for s in ["input.0", "input.1"] + [f"atom.{i}.pbs" for i in range(5)]]
assert all(r["correct"] for r in prev)
errors = [-r["author_measure_noise_scaled"] / Q for r in prev]
predicted = sum(a*e for a,e in zip(alpha,errors))
observed = first["actual"] - first["expected"] - first["author_measure_noise_scaled"] / Q
assert abs(predicted-observed) < 1e-10
assert round(first["expected"]+predicted) % 17 == first["actual"]
controls = [r for r in old if "fresh_and_zero_mask_control" in r.get("stage", "")]
assert len(controls) == 17
assert all(r["expected"] == r["fresh_actual"] == r["zero_mask_actual"] for r in controls)
assert all(r.get("correct", True) and r.get("local_correct", True) for r in new)
assert old[-1]["bitwise_identical"] and new[-1]["bitwise_identical"]
parameter_changes = {k: [old[0]["parameters"][k],new[0]["parameters"][k]]
                     for k in old[0]["parameters"]
                     if old[0]["parameters"][k] != new[0]["parameters"][k]}
assert parameter_changes == {"pbs_base_log": [29,15], "pbs_level": [1,2]}

phase_rows = []
for label, run in [("original_29x1",old),("revised_15x2",new)]:
    for r in run:
        if "author_measure_noise_scaled" not in r:
            continue
        near_error = -r["author_measure_noise_scaled"] / Q
        expected_error = (r["actual"]-r["expected"]+near_error+8.5)%17-8.5
        phase_rows.append({"configuration":label,"stage":r["stage"],
            "expected":r["expected"],"decoded":r["actual"],
            "nearest_grid_error_field_units":near_error,
            "centered_error_relative_to_expected_field_units":expected_error,
            "centered_error_relative_to_expected_torus_units":expected_error/17,
            "correct":r["correct"]})
with (OUT/"stage_phase_analysis.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(phase_rows[0]));w.writeheader();w.writerows(phase_rows)
report = {
    "first_wrong_stage":first,"alpha":alpha,"prior_field_errors":errors,
    "weighted_error_field_units":predicted,"observed_error_field_units":observed,
    "difference":predicted-observed,"predicted_decoding_position":12+predicted,
    "rounding_threshold":0.5,"pbs_fresh_controls":17,"pbs_zero_mask_controls":17,
    "parameter_changes":parameter_changes,
    "revised_all_stage_checks_pass":True,"both_match_original_evaluator_bitwise":True,
    "method":"Author measure_noise reports nearest-grid residual multiplied by 2^64 in field units. We combine that residual with the separately decoded and expected values; we do not mistake a nearest-grid residual for an error relative to the expected value. Coordinates are reconstructed from floating-point diagnostics, not exact integer phase dumps.",
    "hashes":{str(p.relative_to(ROOT)):digest(p) for p in [old_path,new_path,source]},
}
(OUT/"analysis.json").write_text(json.dumps(report,indent=2)+"\n")
original = ROOT/"results/division_fhe_attempt1/source_snapshot.rs"
revised = ROOT/"source/HLUT-rs/src/bin/matched_division_pbs15x2.rs"
(OUT/"benchmark_source.diff").write_text("".join(difflib.unified_diff(
    original.read_text().splitlines(True),revised.read_text().splitlines(True),
    fromfile="original_matched_division.rs",tofile="matched_division_pbs15x2.rs")))
print(json.dumps(report,indent=2))
