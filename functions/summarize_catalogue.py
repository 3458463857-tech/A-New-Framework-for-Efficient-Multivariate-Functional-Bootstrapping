"""Summarize saved catalogue entries; do not run or change experiments.

Run from any directory with Python 3.8 or later. --check compares the derived
files with the saved versions without writing them. No third-party packages
are required.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
METHODS = {
    "BBR26": "bbr_mean_ms",
    "Refined-LHE": "refined_mean_ms",
    "Meta-PBS": "meta_mean_ms",
    "Native": "native_mean_ms",
}


def numeric(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def summarize():
    source = BASE / "catalog.csv"
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 74
    assert len({row["catalog_id"] for row in rows}) == 74
    derived = []
    for row in rows:
        direct = numeric(row["direct_records"])
        records = numeric(row["logical_records"])
        ratio = direct / records if direct is not None and records else None
        ours = numeric(row["ours_mean_ms"])
        measured = []
        lower = []
        for method, column in METHODS.items():
            baseline = numeric(row[column])
            if ours is not None and baseline is not None:
                measured.append(method)
                if ours < baseline:
                    lower.append(method)
        if ours is None:
            latency_status = "not measured"
        elif not lower:
            latency_status = "no lower time than a measured baseline"
        elif len(lower) == len(measured):
            latency_status = "lower time than all measured baselines"
        else:
            latency_status = "lower time than some measured baselines"
        derived.append({
            "catalog_id": row["catalog_id"],
            "function_category": row["function_category"],
            "applicability_label": row["applicability_label"],
            "evidence_type": row["evidence_type"],
            "direct_over_representation_records": "" if ratio is None else format(ratio, ".12g"),
            "record_ratio_scope": row["record_convention"],
            "latency_status": latency_status,
            "measured_baselines": ";".join(measured),
            "lower_time_than": ";".join(lower),
        })

    groups = []
    for category in sorted({row["function_category"] for row in rows}):
        subset = [row for row in rows if row["function_category"] == category]
        ids = {row["catalog_id"] for row in subset}
        derived_subset = [row for row in derived if row["catalog_id"] in ids]
        groups.append({
            "function_category": category,
            "entries": len(subset),
            "structural_instances": sum(row["catalog_id"].startswith("O") for row in subset),
            "measured_configurations": sum(row["catalog_id"].startswith("T") for row in subset),
            "construction_families": sum(row["catalog_id"].startswith("F") for row in subset),
            "measured_with_lower_time_than_at_least_one_baseline": sum(
                bool(row["lower_time_than"]) for row in derived_subset
            ),
            "measured_without_lower_time_than_any_baseline": sum(
                row["latency_status"] == "no lower time than a measured baseline"
                for row in derived_subset
            ),
        })
    ratio_groups = {}
    for label, ids in {
        "elementary_composite_structural_O02_O19": {"O%02d" % i for i in range(2, 20)},
        "order_statistics_structural_O20_O34": {"O%02d" % i for i in range(20, 35)},
        "histogram_statistics_structural_O35_O45": {"O%02d" % i for i in range(35, 46)},
    }.items():
        values = [float(row["direct_over_representation_records"]) for row in derived
                  if row["catalog_id"] in ids]
        ratio_groups[label] = {"entries": len(values), "minimum": min(values), "maximum": max(values)}
    report = {
        "scope": "Reclassification and arithmetic on saved catalogue entries; no new experiment.",
        "catalog_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "entries": len(rows),
        "evidence_group_counts": dict(sorted(Counter(row["catalog_id"][0] for row in rows).items())),
        "applicability_label_counts": dict(sorted(Counter(row["applicability_label"] for row in rows).items())),
        "categories": groups,
        "structural_record_ratios": ratio_groups,
        "limits": [
            "The catalogue contains selected entries; it is not a random sample of functions.",
            "No success probability for a previously unseen function can be estimated from these counts.",
            "The record ratio is direct_records / logical_records, under each row's saved accounting convention.",
            "Missing or symbolic record counts remain blank; no estimate is substituted.",
            "Lower recorded mean does not establish statistical significance or a common-security/reliability ranking.",
            "Comparison-network and histogram counts concern multistep constructions, not one additive representation.",
        ],
    }
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=list(derived[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(derived)
    return {
        "applicability_summary.json": json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        "applicability_records.csv": csv_buffer.getvalue(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify saved summaries without changing files")
    args = parser.parse_args()
    for name, content in summarize().items():
        path = BASE / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("Summary differs: " + name)
            print("Matches saved catalogue: " + name)
        else:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            print("Wrote: " + name)


if __name__ == "__main__":
    main()
