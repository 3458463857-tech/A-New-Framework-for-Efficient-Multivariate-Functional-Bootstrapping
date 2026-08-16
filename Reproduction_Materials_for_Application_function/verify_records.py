#!/usr/bin/env python3
"""Verify the retained records and their independent reruns."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_FIELDS_EXCLUDED = {"elapsed_ms"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def scientific_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {key: value for key, value in row.items() if key not in BASE_FIELDS_EXCLUDED}
        for row in rows
    ]


def main() -> int:
    base_rows = read_csv(ROOT / "results" / "all_results.csv")
    base_rerun = read_csv(ROOT / "verification_rerun" / "all_results.csv")
    base_metadata = json.loads(
        (ROOT / "results" / "results.json").read_text(encoding="utf-8")
    )

    assert len(base_rows) == 76
    assert sum(row["selected"] == "True" for row in base_rows) == 45
    assert base_metadata["result_count"] == 76
    assert base_metadata["selected_count"] == 45
    assert base_metadata["screened_out_count"] == 31
    assert scientific_rows(base_rows) == scientific_rows(base_rerun)

    route_rows = read_csv(ROOT / "intermediate_routes" / "intermediate_routes.csv")
    route_rerun = read_csv(
        ROOT
        / "intermediate_routes_verification_rerun"
        / "intermediate_routes.csv"
    )
    route_metadata = json.loads(
        (ROOT / "intermediate_routes" / "intermediate_routes.json").read_text(
            encoding="utf-8"
        )
    )
    route_rerun_metadata = json.loads(
        (
            ROOT
            / "intermediate_routes_verification_rerun"
            / "intermediate_routes.json"
        ).read_text(encoding="utf-8")
    )

    assert route_rows == route_rerun
    assert route_metadata == route_rerun_metadata
    assert len(route_rows) == 59
    retained = [row for row in route_rows if row["retained"] == "True"]
    assert len(retained) == 45
    assert sum(row["section"] == "elementary" for row in retained) == 19
    assert sum(row["section"] != "elementary" for row in retained) == 26
    assert route_metadata["comparison_count"] == 59
    assert route_metadata["retained_count"] == 45
    assert route_metadata["screened_out_count"] == 14

    print(
        "PASS base study: 76 candidates, 45 retained; independent scientific "
        "fields match."
    )
    print(
        "PASS intermediate routes: 59 comparisons, 45 retained "
        "(19 elementary and 26 further functions); independent rerun matches."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
