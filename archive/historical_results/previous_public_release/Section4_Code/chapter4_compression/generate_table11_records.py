#!/usr/bin/env python3
"""Generate the verified Section-4 representations consumed by Table 11.

The output is intentionally both human-readable JSON and a flat CSV that the
Rust benchmark can parse without adding a serialization dependency.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from compress import anneal_symmetric, indicator_representation, verify
from functions import lower_median, symbol_set_interval, symbol_set_threshold


Point = tuple[int, ...]
Target = Callable[[Point], int]


def hamming_interval(point: Point) -> int:
    return int(4 <= sum(point) <= 6)


def case_record(
    *,
    case_id: str,
    function: str,
    t: int,
    ell: int,
    parameters: dict[str, object],
    method: str,
    representation: list[list[int]],
    target: Target,
    search: dict[str, object] | None = None,
) -> dict[str, object]:
    report = verify(representation, t, target)
    if not report.valid:
        raise AssertionError(f"invalid representation for {case_id}: {report.conflict}")
    return {
        "case_id": case_id,
        "function": function,
        "t": t,
        "ell": ell,
        "parameters": parameters,
        "method": method,
        "representation": representation,
        "span": report.span,
        "minimum_sum": report.minimum_sum,
        "maximum_sum": report.maximum_sum,
        "distinct_sums": report.distinct_sums,
        "outer_table": {str(key): value for key, value in report.outer_table.items()},
        "exhaustive_points": t**ell,
        "exhaustive_verification": True,
        "search": search,
    }


def build_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    ell, t = 10, 2
    representation = indicator_representation(ell, t, {1})
    records.append(
        case_record(
            case_id="hamming_weight_interval",
            function="Hamming-weight interval",
            t=t,
            ell=ell,
            parameters={"lower": 4, "upper": 6},
            method="explicit Hamming-weight representation",
            representation=representation,
            target=hamming_interval,
        )
    )

    ell, t, symbols = 6, 4, {1, 3}
    representation = indicator_representation(ell, t, symbols)
    records.append(
        case_record(
            case_id="symbol_set_interval",
            function="General symbol-set interval",
            t=t,
            ell=ell,
            parameters={"symbols": sorted(symbols), "lower": 2, "upper": 4},
            method="explicit count representation",
            representation=representation,
            target=lambda point: symbol_set_interval(point, symbols, 2, 4),
        )
    )

    symbols = {0, 2}
    representation = indicator_representation(ell, t, symbols)
    records.append(
        case_record(
            case_id="symbol_set_threshold",
            function="General symbol-set threshold",
            t=t,
            ell=ell,
            parameters={"symbols": sorted(symbols), "threshold": 3},
            method="explicit count representation",
            representation=representation,
            target=lambda point: symbol_set_threshold(point, symbols, 3),
        )
    )

    representation, report, trace = anneal_symmetric(
        6,
        3,
        lower_median,
        iterations=20_000,
        restarts=8,
        seed=20260810,
        max_score=12,
        target_span=42,
    )
    if report.span != 42:
        raise AssertionError(f"expected the published median span 42, got {report.span}")
    records.append(
        case_record(
            case_id="lower_median",
            function="Lower median",
            t=3,
            ell=6,
            parameters={"tie_rule": "lower median for even ell"},
            method="deterministic symmetric simulated annealing",
            representation=representation,
            target=lower_median,
            search=asdict(trace),
        )
    )
    return records


def write_records(records: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "table11_representations.json"
    csv_path = output_dir / "table11_representations.csv"
    json_path.write_text(
        json.dumps({"format_version": 2, "cases": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "case_id",
                "t",
                "ell",
                "coordinate",
                "input",
                "score",
                "method",
                "seed",
                "iterations",
                "span",
                "distinct_sums",
            )
        )
        for record in records:
            search = record.get("search") or {}
            for coordinate, row in enumerate(record["representation"]):
                for value, score in enumerate(row):
                    writer.writerow(
                        (
                            record["case_id"],
                            record["t"],
                            record["ell"],
                            coordinate,
                            value,
                            score,
                            record["method"],
                            search.get("seed", ""),
                            search.get("iterations", ""),
                            record["span"],
                            record["distinct_sums"],
                        )
                    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "records",
    )
    args = parser.parse_args()
    records = build_records()
    write_records(records, args.output_dir)
    for record in records:
        message = (
            f"PASS {record['case_id']}: span={record['span']}, "
            f"distinct_sums={record['distinct_sums']}, points={record['exhaustive_points']}"
        )
        search = record.get("search")
        if search:
            message += (
                f", seed={search['seed']}, iterations_executed={search['iterations_executed']}, "
                f"restarts_executed={search['restarts_executed']}"
            )
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
