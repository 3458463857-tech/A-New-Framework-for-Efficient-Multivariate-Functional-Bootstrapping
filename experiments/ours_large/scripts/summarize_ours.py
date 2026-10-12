"""Validate source/input binding and summarize the ten frozen measurements."""
import csv
import hashlib
import io
import json
import statistics
from pathlib import Path
from task_definitions import TASKS, target

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "ours/results/protocol1_attempt1"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def quantile(values, p):
    values = sorted(values)
    index = (len(values)-1)*p
    lo = int(index)
    hi = min(lo+1,len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(index-lo)

def main():
    assert (RUN/"finished.txt").exists(), "run incomplete; do not publish a partial summary"
    source = ROOT/"ours/src/bin/functions_checked.rs"
    assert source.read_bytes() == (RUN/"source_snapshot.rs").read_bytes()
    assert source.read_bytes() == (ROOT/"ours/results/build_attempt1/source_snapshot.rs").read_bytes()
    assert (ROOT/"ours/Cargo.lock").read_bytes() == (RUN/"Cargo.lock").read_bytes()
    assert (ROOT/"ours/Cargo.toml").read_bytes() == (RUN/"Cargo.toml").read_bytes()
    manifest = json.loads((ROOT/"inputs/manifest.json").read_text())
    assert sha(Path(__file__).with_name("task_definitions.py")) == manifest["definitions_sha256"]
    manifest_by_id = {r["task_id"]: r for r in manifest["files"]}
    rust_cert = {r["task_id"]:r for r in csv.DictReader((RUN/"plaintext_rust_certificate.csv").open())}
    py_cert = {r["task_id"]:r for r in json.loads((ROOT/"inputs/plaintext_certificates.json").read_text())}
    summary = []
    for task_id, (t,n) in TASKS.items():
        folder = RUN/task_id
        assert (folder/"exit_code.txt").read_text().strip() == "0"
        input_path = ROOT/"inputs"/(task_id+".csv")
        assert sha(input_path) == manifest_by_id[task_id]["sha256"]
        assert input_path.read_bytes() == (folder/"input_snapshot.csv").read_bytes()
        input_rows = list(csv.DictReader(input_path.open()))
        lines = (folder/"run.log").read_text().splitlines()
        assert lines[-1] == f"COMPLETE,task={task_id},warmups=5,measured=30,mismatches=0"
        header = lines.index("phase,index,task_id,inputs,expected,actual,pbs_count,total_ms,outer_degree,outer_noise,output_degree,output_noise,kind")
        rows = list(csv.DictReader(io.StringIO("\n".join(lines[header:-1]))))
        assert len(rows)==35
        for row, given in zip(rows,input_rows):
            for field in given: assert row[field] == given[field], (task_id,field,row,given)
            xs = list(map(int,row["inputs"].split(';')))
            expected = target(task_id,xs)
            assert int(row["expected"]) == int(row["actual"]) == expected
            assert int(row["pbs_count"]) == (1 if t==2 else 3)
            assert int(row["output_noise"]) == 1
            assert int(row["output_degree"]) < (2 if t==2 else 4)
            assert int(row["outer_degree"]) < (32 if t==2 else 64)
            assert int(row["outer_noise"]) <= (31 if t==2 else 21)
        measured = [r for r in rows if r["phase"]=="measured"]
        assert len(measured)==30
        for key, rustkey in [("cartesian_inputs","cartesian_inputs"),("reachable_scores","reachable_scores"),("score_max","maximum_score")]:
            assert py_cert[task_id][key] == int(rust_cert[task_id][rustkey])
        assert rust_cert[task_id]["check"] == "PASS"
        times = [float(r["total_ms"]) for r in measured]
        summary.append({"task_id":task_id,"t":t,"n":n,
            "parameter":"PARAM_MULTI_BIT_GROUP_3_MESSAGE_1_CARRY_4_KS_PBS_GAUSSIAN_2M64" if t==2 else "PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_4_KS_PBS_GAUSSIAN_2M64",
            "pbs_count":int(measured[0]["pbs_count"]),"warmups":5,"samples":30,"correct_outputs":35,
            "mean_ms":statistics.mean(times),"sample_sd_ms":statistics.stdev(times),
            "median_ms":statistics.median(times),"p95_ms":quantile(times,.95),"min_ms":min(times),"max_ms":max(times),
            "maximum_observed_outer_degree":max(int(r["outer_degree"]) for r in rows),
            "maximum_observed_outer_noise":max(int(r["outer_noise"]) for r in rows),
            "cartesian_inputs_checked":py_cert[task_id]["cartesian_inputs"],
            "source_sha256":sha(source),"input_sha256":sha(input_path),"log_sha256":sha(folder/"run.log")})
    out=ROOT/"ours/summary";out.mkdir(exist_ok=True)
    (out/"results.json").write_text(json.dumps({"protocol":"functions_v4_frozen10","rows":summary,
        "statistics":"sample SD (ddof=1), p95 by linear interpolation of sorted samples",
        "source_input_binding":"PASS","total_correct_outputs":sum(r["correct_outputs"] for r in summary)},indent=2)+"\n")
    with (out/"results.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    print(json.dumps({"tasks":len(summary),"correct_outputs":sum(r["correct_outputs"] for r in summary),"binding":"PASS"}))
    for r in summary: print(f"{r['task_id']},{r['pbs_count']},{r['mean_ms']:.6f},{r['sample_sd_ms']:.6f}")

if __name__=="__main__":main()
