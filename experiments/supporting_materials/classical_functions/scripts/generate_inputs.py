"""Deterministic manifests and exhaustive plaintext certificates (stdlib only)."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
from task_definitions import TASKS, target, score

ROOT = Path(__file__).resolve().parents[1]
MASK = (1 << 64) - 1

class SplitMix64:
    def __init__(self, seed): self.state = seed
    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)
    def uniform(self, bound):
        limit = (1 << 64) - ((1 << 64) % bound)
        while True:
            value = self.next()
            if value < limit: return value % bound

def boundaries(task_id):
    if task_id == "hamming_interval10":
        return [("weight_" + str(k), [1] * k + [0] * (10-k)) for k in (0,10,3,4,5,6,7,1,9,2)]
    if task_id == "set_interval4_6":
        return [("member_count_" + str(k), [1]*k + [0]*(6-k)) for k in (0,6,1,2,3,4,5)] + [
            ("mixed_symbols", [0,1,2,3,0,1]), ("all_three", [3]*6), ("all_two", [2]*6)]
    if task_id == "set_threshold4_6":
        return [("member_count_" + str(k), [0]*k + [1]*(6-k)) for k in (0,6,2,3,4,1,5)] + [
            ("all_two", [2]*6), ("all_three", [3]*6), ("mixed_symbols", [0,1,2,3,2,3])]
    return [
        ("all_zero", [0]*6), ("all_one", [1]*6), ("all_two", [2]*6),
        ("tie_zero_one", [0,0,0,1,1,1]), ("tie_one_two", [1,1,1,2,2,2]),
        ("three_way_tie", [0,0,1,1,2,2]), ("four_zero_two_two", [0,0,0,0,2,2]),
        ("two_zero_four_two", [0,0,2,2,2,2]), ("four_one_extremes", [0,1,1,1,1,2]),
        ("lower_median_boundary", [0,0,0,1,2,2]),
    ]

def main():
    out = ROOT / "inputs"; out.mkdir(parents=True, exist_ok=True)
    certificates = []; files = []
    for task_id, (t,n) in TASKS.items():
        seed = 20261010 + 1000*t + n
        rng = SplitMix64(seed)
        warmups = [[(i+j) % t for i in range(n)] for j in range(5)]
        rows = [("warmup",i,task_id,xs,target(task_id,xs),"cyclic_warmup") for i,xs in enumerate(warmups)]
        rows += [("measured",i,task_id,xs,target(task_id,xs),kind) for i,(kind,xs) in enumerate(boundaries(task_id))]
        for i in range(20):
            xs = [rng.uniform(t) for _ in range(n)]
            rows.append(("measured",10+i,task_id,xs,target(task_id,xs),"splitmix64_uniform"))
        assert len(rows) == 35
        path = out / (task_id + ".csv")
        with path.open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f,lineterminator="\n")
            writer.writerow(["phase","index","task_id","inputs","expected","kind"])
            for phase,index,name,xs,y,kind in rows:
                writer.writerow([phase,index,name,";".join(map(str,xs)),y,kind])
        mapping = {}; count = 0
        for xs in itertools.product(range(t),repeat=n):
            z = score(task_id,xs); y = target(task_id,xs)
            assert z not in mapping or mapping[z] == y, (task_id,xs,z,y,mapping[z])
            mapping[z] = y; count += 1
        certificate={"task_id":task_id,"domain":[t,n],"cartesian_inputs":count,
            "reachable_scores":len(mapping),"score_min":min(mapping),"score_max":max(mapping),
            "output_values":sorted(set(mapping.values())),"outer_table":{str(k):v for k,v in sorted(mapping.items())},
            "result":"PASS"}
        certificates.append(certificate)
        files.append({"task_id":task_id,"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "seed":seed,"warmups":5,"boundary_samples":10,"random_samples":20,"measured":30})
    definition = Path(__file__).with_name("task_definitions.py")
    (out/"manifest.json").write_text(json.dumps({"protocol":"functions_v4_frozen10",
        "schema":"phase,index,task_id,inputs,expected,kind","random":"SplitMix64 with unbiased rejection per coordinate",
        "shared_random_inputs":"same alphabet and arity use the same seed and random vectors",
        "definitions_sha256":hashlib.sha256(definition.read_bytes()).hexdigest(),"files":files},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"plaintext_certificates.json").write_text(json.dumps(certificates,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tasks":len(files),"manifest_rows":sum(x["warmups"]+x["measured"] for x in files),
        "exhaustive_plaintext_inputs":sum(x["cartesian_inputs"] for x in certificates),"result":"PASS"}))

if __name__ == "__main__": main()
