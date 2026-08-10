#!/usr/bin/env python3
"""Cross-check both experiment outputs against the English TeX tables."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NOTE = ROOT.parent / "applicable_functions.tex"
BASE_RESULTS = ROOT / "results"
ROUTE_RESULTS = ROOT / "intermediate_routes"


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main() -> int:
    base_rows = list(csv.DictReader((BASE_RESULTS / "all_results.csv").open(encoding="utf-8")))
    base_metadata = json.loads((BASE_RESULTS / "results.json").read_text(encoding="utf-8"))
    base_selected = [row for row in base_rows if row["selected"] == "True"]
    assert len(base_rows) == base_metadata["result_count"] == 76
    assert len(base_selected) == base_metadata["selected_count"] == 45
    assert base_metadata["screened_out_count"] == 31
    assert all(row["exact"] == "True" for row in base_selected)
    assert all(int(row["maximum_error"]) == 0 for row in base_selected)

    route_rows = list(csv.DictReader(
        (ROUTE_RESULTS / "intermediate_routes.csv").open(encoding="utf-8")
    ))
    route_metadata = json.loads(
        (ROUTE_RESULTS / "intermediate_routes.json").read_text(encoding="utf-8")
    )
    route_selected = [row for row in route_rows if row["retained"] == "True"]
    elementary = [row for row in route_selected if row["section"] == "elementary"]
    general = [row for row in route_selected if row["section"] != "elementary"]
    assert len(route_rows) == route_metadata["comparison_count"] == 59
    assert len(route_selected) == route_metadata["retained_count"] == 45
    assert len(elementary) == route_metadata["retained_elementary_count"] == 19
    assert len(general) == route_metadata["retained_general_count"] == 26
    assert route_metadata["screened_out_count"] == 14
    assert all(row["exact"] == "True" for row in route_rows)
    assert all(int(row["our_records"]) < int(row["alternative_records"]) for row in route_selected)

    tex = NOTE.read_text(encoding="utf-8")
    assert "base run contains 76 parameterized candidates" in tex
    assert re.search(r"checks\s+59 function/parameter rows", tex)
    assert "LUT\\\\evals." in tex and "Calls" not in tex
    assert "Alt./ours" in tex

    elementary_block = tex.split(r"\label{tab:elementary}", 1)[1].split(
        r"\end{longtable}", 1
    )[0]
    elementary_compact = compact(elementary_block)
    for row in elementary:
        numeric_run = (
            f'{row["direct_records"]}&{row["output_cardinality"]}&'
            f'{row["our_records"]}&'
        )
        assert numeric_run in elementary_compact, row["function"]

    general_block = tex.split(r"\label{tab:general}", 1)[1].split(
        r"\end{longtable}", 1
    )[0]
    general_compact = compact(general_block)
    general_lower = general_block.lower()
    for row in general:
        numeric_run = (
            f'{row["direct_records"]}&{row["output_cardinality"]}&'
            f'{row["our_records"]}&{row["alternative_records"]}&'
        )
        assert numeric_run in general_compact, row["function"]
        assert row["function"].lower() in general_lower, row["function"]

    rejected_table_labels = (
        "integer rms", "variance bucket", "winsorized mean",
        "second frequency moment", "collision-pair count", "gini bucket",
        "quantized jaccard", "quantized dice", "quantized cosine",
        "quantized overlap", "levenshtein", "longest-common-subsequence",
        "dynamic time-warping", "frechet distance",
    )
    assert all(label not in general_lower for label in rejected_table_labels)

    trigonometric = [
        row for row in base_rows
        if "sin(pi" in row["function"] or "tan(pi" in row["function"]
        or "cos(pi" in row["function"]
    ]
    assert trigonometric
    assert all(row["exact"] == "True" for row in trigonometric)
    assert all(row["selected"] == "False" for row in trigonometric)

    print(
        "PASS: 76 base rows; 59 intermediate-route comparisons; "
        "19 elementary and 26 further rows checked against the TeX tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
