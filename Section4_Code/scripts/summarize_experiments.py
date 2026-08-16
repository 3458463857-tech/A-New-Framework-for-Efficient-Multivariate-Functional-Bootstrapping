#!/usr/bin/env python3
"""Parse the output-checked Table 11 log into CSV and JSON records."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def read_prefixed(path: Path, prefix: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix + ","):
            rows.append(next(csv.reader([line])))
    return rows


def parse_table11(run_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    path = run_dir / "table11.log"
    runs: list[dict[str, object]] = []
    for row in read_prefixed(path, "TABLE11_RESULT"):
        runs.append(
            {
                "case_id": row[1],
                "repetition": int(row[2]),
                "inputs": row[3],
                "actual": int(row[4]),
                "online_ms": float(row[5]),
            }
        )

    summaries: list[dict[str, object]] = []
    for row in read_prefixed(path, "TABLE11_SUMMARY"):
        summaries.append(
            {
                "case_id": row[1],
                "t": int(row[2]),
                "ell": int(row[3]),
                "pbs_calls": int(row[4]),
                "span": int(row[5]),
                "representation_method": row[6],
                "annealing_seed": row[7] or None,
                "average_online_ms": float(row[8]),
                "stddev_ms": float(row[9]),
                "median_ms": float(row[10]),
                "minimum_ms": float(row[11]),
                "maximum_ms": float(row[12]),
                "all_outputs_checked": True,
            }
        )

    expected_calls = {
        "hamming_weight_interval": 1,
        "symbol_set_interval": 3,
        "symbol_set_threshold": 3,
        "lower_median": 3,
    }
    actual_calls = {str(row["case_id"]): int(row["pbs_calls"]) for row in summaries}
    if actual_calls != expected_calls:
        raise RuntimeError(
            f"Table 11 PBS counts do not match the three-variable packing: {actual_calls}"
        )
    return runs, summaries


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cross_check(
    runs: list[dict[str, object]],
    summaries: list[dict[str, object]],
    expected_repetitions: int,
) -> None:
    for summary in summaries:
        selected = [
            float(row["online_ms"])
            for row in runs
            if row["case_id"] == summary["case_id"]
        ]
        if len(selected) != expected_repetitions:
            raise AssertionError(f"run count mismatch for {summary['case_id']}")
        if abs(statistics.fmean(selected) - float(summary["average_online_ms"])) > 1e-5:
            raise AssertionError(f"average mismatch for {summary['case_id']}")


def read_environment(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    environment = read_environment(args.run_dir / "environment_kv.txt")
    repetitions = int(environment["repetitions"])
    runs, summaries = parse_table11(args.run_dir)
    cross_check(runs, summaries, repetitions)
    write_csv(args.run_dir / "table11_runs.csv", runs)
    write_csv(args.run_dir / "table11_summary.csv", summaries)
    (args.run_dir / "summary.json").write_text(
        json.dumps(
            {
                "table11": summaries,
                "policy": {
                    "timed_region": "online homomorphic evaluation only",
                    "excluded": [
                        "key generation",
                        "LUT generation",
                        "input encryption",
                        "output decryption",
                    ],
                    "correctness": "every timed output decrypted and checked",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(args.run_dir / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
