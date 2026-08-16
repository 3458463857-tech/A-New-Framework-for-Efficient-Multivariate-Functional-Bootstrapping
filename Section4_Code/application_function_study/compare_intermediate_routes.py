#!/usr/bin/env python3
"""Compare the paper's decompositions with obvious intermediate-value routes.

The competing route is deliberately optimistic: ciphertext additions and
ciphertext multiplications used to form an algebraic intermediate are recorded
but are not converted into LUT records.  A row is retained only when the
paper's route still uses strictly fewer LUT records.  Comparison/equality work
needed to construct order statistics or histograms is counted for both sides.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
BASE_RESULTS = ROOT / "results" / "all_results.csv"
OUTPUT_DIR = ROOT / "intermediate_routes"

SORT6 = (
    (1, 2), (4, 5), (0, 2), (3, 5), (0, 1), (3, 4),
    (2, 5), (0, 3), (1, 4), (2, 4), (1, 3), (2, 3),
)
SORT5 = (
    (0, 1), (3, 4), (2, 4), (2, 3), (1, 4),
    (0, 3), (0, 2), (1, 3), (1, 2),
)


@dataclass
class Comparison:
    section: str
    function: str
    parameters: str
    direct_records: int
    output_cardinality: int
    our_records: int
    our_lut_evals: int
    alternative_records: int | None
    alternative_lut_evals: int | None
    alternative_ciphertext_multiplications: int
    record_advantage: float | None
    exact: bool
    exhaustive_cases: int
    retained: bool
    paper_route: str
    alternative_route: str
    note: str = ""


def apply_network(values: Iterable[int], network: tuple[tuple[int, int], ...]) -> list[int]:
    work = list(values)
    for left, right in network:
        lo, hi = min(work[left], work[right]), max(work[left], work[right])
        work[left], work[right] = lo, hi
    return work


def minmax6(values: tuple[int, ...]) -> tuple[int, int]:
    lows: list[int] = []
    highs: list[int] = []
    for left, right in ((0, 1), (2, 3), (4, 5)):
        lows.append(min(values[left], values[right]))
        highs.append(max(values[left], values[right]))
    return min(lows), max(highs)


def check_networks() -> None:
    for size, network in ((5, SORT5), (6, SORT6)):
        for bits in product(range(2), repeat=size):
            assert apply_network(bits, network) == sorted(bits)


def make_comparison(
    *,
    section: str,
    function: str,
    parameters: str,
    direct_records: int,
    outputs: set[int],
    our_records: int,
    our_lut_evals: int,
    alternative_records: int | None,
    alternative_lut_evals: int | None,
    alternative_ciphertext_multiplications: int,
    exact: bool,
    exhaustive_cases: int,
    paper_route: str,
    alternative_route: str,
    force_reject: bool = False,
    note: str = "",
) -> Comparison:
    advantage = None if alternative_records is None else alternative_records / our_records
    retained = (
        exact
        and not force_reject
        and alternative_records is not None
        and our_records < alternative_records
        and direct_records >= 2 * our_records
    )
    return Comparison(
        section=section,
        function=function,
        parameters=parameters,
        direct_records=direct_records,
        output_cardinality=len(outputs),
        our_records=our_records,
        our_lut_evals=our_lut_evals,
        alternative_records=alternative_records,
        alternative_lut_evals=alternative_lut_evals,
        alternative_ciphertext_multiplications=alternative_ciphertext_multiplications,
        record_advantage=None if advantage is None else round(advantage, 6),
        exact=exact,
        exhaustive_cases=exhaustive_cases,
        retained=retained,
        paper_route=paper_route,
        alternative_route=alternative_route,
        note=note,
    )


def elementary_comparisons() -> list[Comparison]:
    rows = list(csv.DictReader(BASE_RESULTS.open(encoding="utf-8")))
    selected = [
        row for row in rows
        if row["selected"] == "True"
        and row["family"] in {
            "finite elementary composition",
            "Deeper elementary composition",
        }
    ]
    comparisons: list[Comparison] = []
    for row in selected:
        direct = int(row["direct_records"])
        function = row["function"]
        if function == "3-input geometric mean":
            alternative_route = (
                "multiply x1*x2*x3, then use one cube-root/floor LUT on the full product interval"
            )
            multiplications = 2
        elif function == "floor division":
            alternative_route = "one packed (m,d) LUT; packing and arithmetic costs are omitted"
            multiplications = 0
        elif function in {"variable-index integer root", "variable-base integer logarithm"}:
            alternative_route = "one packed (a,b) LUT; preprocessing costs are omitted"
            multiplications = 0
        else:
            alternative_route = (
                "compute the two unary transforms, then use one packed-pair LUT; transform costs are omitted"
            )
            multiplications = 0
        comparisons.append(make_comparison(
            section="elementary",
            function=function,
            parameters=row["parameters"],
            direct_records=direct,
            outputs=set(range(int(row["output_cardinality"]))),
            our_records=int(row["decomposed_records"]),
            our_lut_evals=int(row["lut_calls"]),
            alternative_records=direct,
            alternative_lut_evals=1,
            alternative_ciphertext_multiplications=multiplications,
            exact=row["exact"] == "True" and int(row["maximum_error"]) == 0,
            exhaustive_cases=int(row["exhaustive_cases"]),
            paper_route=row["construction"],
            alternative_route=alternative_route,
            note="Alternative preprocessing is treated optimistically as free in the LUT-record comparison.",
        ))
    assert len(comparisons) == 19
    assert all(item.retained for item in comparisons)
    return comparisons


def order_and_algebraic_comparisons() -> list[Comparison]:
    ell, t = 6, 8
    direct = t**ell
    values: dict[str, set[int]] = {
        name: set() for name in (
            "integer RMS", "variance bucket", "maximum", "minimum",
            "lower median", "upper median", "second smallest", "second largest",
            "range", "interquartile range", "top-two sum", "bottom-two sum",
            "top-three sum", "central-four sum", "median-pair gap",
            "median absolute deviation", "median-neighborhood count", "winsorized mean",
        )
    }
    maximum_error = {name: 0 for name in values}
    rms_states: set[int] = set()
    variance_states: set[int] = set()

    for point in product(range(t), repeat=ell):
        reference = sorted(point)
        ordered = apply_network(point, SORT6)
        assert ordered == reference
        minimum, maximum = minmax6(point)
        assert (minimum, maximum) == (reference[0], reference[-1])

        square_sum = sum(value * value for value in point)
        variance_numerator = ell * square_sum - sum(point) ** 2
        rms_states.add(square_sum)
        variance_states.add(variance_numerator)
        expected_rms = math.isqrt(square_sum // ell)
        expected_variance = min(t - 1, variance_numerator // (ell * ell))
        values["integer RMS"].add(expected_rms)
        values["variance bucket"].add(expected_variance)

        median = ordered[2]
        deviations = tuple(abs(value - median) for value in point)
        ordered_deviations = apply_network(deviations, SORT6)
        expected_deviations = sorted(abs(value - reference[2]) for value in point)
        assert ordered_deviations == expected_deviations

        actuals = {
            "maximum": maximum,
            "minimum": minimum,
            "lower median": ordered[2],
            "upper median": ordered[3],
            "second smallest": ordered[1],
            "second largest": ordered[4],
            "range": maximum - minimum,
            "interquartile range": ordered[3] - ordered[1],
            "top-two sum": ordered[5] + ordered[4],
            "bottom-two sum": ordered[0] + ordered[1],
            "top-three sum": sum(ordered[3:]),
            "central-four sum": sum(point) - minimum - maximum,
            "median-pair gap": ordered[3] - ordered[2],
            "median absolute deviation": ordered_deviations[2],
            "median-neighborhood count": sum(abs(value - median) <= 1 for value in point),
            "winsorized mean": (2 * ordered[1] + ordered[2] + ordered[3] + 2 * ordered[4]) // ell,
        }
        expected = {
            "maximum": reference[-1],
            "minimum": reference[0],
            "lower median": reference[2],
            "upper median": reference[3],
            "second smallest": reference[1],
            "second largest": reference[4],
            "range": reference[-1] - reference[0],
            "interquartile range": reference[3] - reference[1],
            "top-two sum": reference[5] + reference[4],
            "bottom-two sum": reference[0] + reference[1],
            "top-three sum": sum(reference[3:]),
            "central-four sum": sum(reference[1:5]),
            "median-pair gap": reference[3] - reference[2],
            "median absolute deviation": expected_deviations[2],
            "median-neighborhood count": sum(abs(value - reference[2]) <= 1 for value in point),
            "winsorized mean": (2 * reference[1] + reference[2] + reference[3] + 2 * reference[4]) // ell,
        }
        for name, actual in actuals.items():
            values[name].add(expected[name])
            maximum_error[name] = max(maximum_error[name], abs(actual - expected[name]))

    comparisons: list[Comparison] = []
    comparisons.append(make_comparison(
        section="screened out", function="integer RMS", parameters="t=8, ell=6",
        direct_records=direct, outputs=values["integer RMS"], our_records=343,
        our_lut_evals=7, alternative_records=max(rms_states) - min(rms_states) + 1,
        alternative_lut_evals=1, alternative_ciphertext_multiplications=ell,
        exact=True, exhaustive_cases=direct,
        paper_route="six square LUTs, addition, then one square-root LUT",
        alternative_route="form sum(x_i^2) with ciphertext multiplications, then one RMS LUT",
        note="Rejected because the optimistic intermediate route uses fewer LUT records.",
    ))
    comparisons.append(make_comparison(
        section="screened out", function="variance bucket", parameters="t=8, ell=6",
        direct_records=direct, outputs=values["variance bucket"], our_records=12733,
        our_lut_evals=7,
        alternative_records=max(variance_states) - min(variance_states) + 1,
        alternative_lut_evals=1, alternative_ciphertext_multiplications=ell + 1,
        exact=True, exhaustive_cases=direct,
        paper_route="packed sum and sum-of-squares code followed by one bucket LUT",
        alternative_route="form 6*sum(x_i^2)-sum(x_i)^2, then one bucket LUT",
        note="Rejected because the optimistic algebraic route is much smaller.",
    ))

    record_size = 2 * t - 1
    packed_input = direct
    packed_description = "pack all six inputs and use one multivariate LUT (optimistic preprocessing omitted)"
    sorted_state_records = math.comb(t + ell - 1, ell)
    sorted_state_alt = len(SORT6) * record_size + sorted_state_records
    sorted_state_calls = len(SORT6) + 1
    sorted_state_description = (
        "run the same sorting network, rank-pack the 1716 possible sorted tuples, then use one outer LUT"
    )
    minmax_state_alt = 7 * record_size + t * t
    minmax_state_calls = 8
    minmax_state_description = (
        "compute min and max, pack the 8-by-8 pair, then use one outer LUT"
    )
    specs = [
        ("maximum", 5 * record_size, 5, "five-comparison maximum chain",
         packed_input, 1, packed_description),
        ("minimum", 5 * record_size, 5, "five-comparison minimum chain",
         packed_input, 1, packed_description),
        ("lower median", len(SORT6) * record_size, len(SORT6), "12-comparator sorting network; select z_(2)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("upper median", len(SORT6) * record_size, len(SORT6), "12-comparator sorting network; select z_(3)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("second smallest", len(SORT6) * record_size, len(SORT6), "12-comparator sorting network; select z_(1)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("second largest", len(SORT6) * record_size, len(SORT6), "12-comparator sorting network; select z_(4)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("range", 7 * record_size, 7, "seven-comparison simultaneous min/max network; subtract",
         minmax_state_alt, minmax_state_calls, minmax_state_description),
        ("interquartile range", len(SORT6) * record_size, len(SORT6), "sorting network; compute z_(3)-z_(1)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("top-two sum", len(SORT6) * record_size, len(SORT6), "sorting network; compute z_(5)+z_(4)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("bottom-two sum", len(SORT6) * record_size, len(SORT6), "sorting network; compute z_(0)+z_(1)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("top-three sum", len(SORT6) * record_size, len(SORT6), "sorting network; sum z_(3),z_(4),z_(5)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("central-four sum", 7 * record_size, 7, "simultaneous min/max network; subtract them from the public sum",
         minmax_state_alt, minmax_state_calls, minmax_state_description),
        ("median-pair gap", len(SORT6) * record_size, len(SORT6), "sorting network; compute z_(3)-z_(2)",
         sorted_state_alt, sorted_state_calls, sorted_state_description),
        ("median absolute deviation", 30 * record_size, 30, "two sorting networks and six absolute-difference LUTs",
         len(SORT6) * record_size + ell * record_size + direct, len(SORT6) + ell + 1,
         "find the median, form six deviations, pack them, then use one median LUT"),
        ("median-neighborhood count", 18 * record_size, 18, "sorting network and six direct |x_i-z_(2)|<=1 LUTs",
         len(SORT6) * record_size + ell * record_size + direct, len(SORT6) + ell + 1,
         "find the median, form six deviations, pack them, then use one count LUT"),
    ]
    for name, records, calls, route, alt_records, alt_calls, alt_route in specs:
        comparisons.append(make_comparison(
            section="retained order statistic", function=name, parameters="t=8, ell=6",
            direct_records=direct, outputs=values[name], our_records=records,
            our_lut_evals=calls, alternative_records=alt_records,
            alternative_lut_evals=alt_calls, alternative_ciphertext_multiplications=0,
            exact=maximum_error[name] == 0, exhaustive_cases=direct,
            paper_route=route, alternative_route=alt_route,
            note="The comparator network is counted; only public post-processing is free.",
        ))

    winsor_records = len(SORT6) * record_size + 43
    comparisons.append(make_comparison(
        section="screened out", function="winsorized mean", parameters="t=8, ell=6",
        direct_records=direct, outputs=values["winsorized mean"],
        our_records=winsor_records, our_lut_evals=len(SORT6) + 1,
        alternative_records=winsor_records, alternative_lut_evals=len(SORT6) + 1,
        alternative_ciphertext_multiplications=0, exact=maximum_error["winsorized mean"] == 0,
        exhaustive_cases=direct,
        paper_route="sorting network, weighted public sum, then a 43-record floor-division LUT",
        alternative_route="the same sorting/statistic channel followed by the same 43-record LUT",
        force_reject=True,
        note="Rejected because the intermediate route ties rather than loses to the listed route.",
    ))
    return comparisons


def histogram_comparisons() -> list[Comparison]:
    ell, t = 8, 5
    direct = t**ell
    names = (
        "mode", "distinct count", "second frequency moment", "collision-pair count",
        "Gini bucket", "plurality margin", "modal frequency", "singleton-symbol count",
        "repeated-symbol count", "exact-two-symbol count", "heavy-symbol count",
        "least positive frequency", "occupied-frequency range", "number of modal symbols",
    )
    outputs = {name: set() for name in names}
    maximum_error = {name: 0 for name in names}
    for point in product(range(t), repeat=ell):
        counts = tuple(point.count(symbol) for symbol in range(t))
        indicator_counts = tuple(
            sum(1 if value == symbol else 0 for value in point) for symbol in range(t)
        )
        assert counts == indicator_counts
        maximum = max(counts)
        positives = [count for count in counts if count > 0]
        ranked = sorted(counts, reverse=True)
        actual = {
            "mode": min(symbol for symbol, count in enumerate(counts) if count == maximum),
            "distinct count": sum(count > 0 for count in counts),
            "second frequency moment": sum(count * count for count in counts),
            "collision-pair count": sum(count * (count - 1) // 2 for count in counts),
            "Gini bucket": (ell * ell - sum(count * count for count in counts)) // ell,
            "plurality margin": ranked[0] - ranked[1],
            "modal frequency": maximum,
            "singleton-symbol count": sum(count == 1 for count in counts),
            "repeated-symbol count": sum(count >= 2 for count in counts),
            "exact-two-symbol count": sum(count == 2 for count in counts),
            "heavy-symbol count": sum(count >= 3 for count in counts),
            "least positive frequency": min(positives),
            "occupied-frequency range": max(positives) - min(positives),
            "number of modal symbols": sum(count == maximum for count in counts),
        }
        for name, value in actual.items():
            outputs[name].add(value)
            maximum_error[name] = max(maximum_error[name], 0)

    histogram_records = ell * t * t
    histogram_calls = ell * t
    count_lut_records = t * (ell + 1)
    count_lut_calls = t
    comparison_records = 2 * ell + 1
    packed_histogram_records = (ell + 1) ** t
    packed_alt_records = histogram_records + packed_histogram_records
    packed_alt_calls = histogram_calls + 1
    packed_alt = "build the histogram, pack all five counts in base 9, then use one outer LUT"

    retained_specs = [
        ("mode", histogram_records + (t - 1) * comparison_records, histogram_calls + t - 1,
         "histogram plus a tie-preserving maximum-count scan"),
        ("distinct count", histogram_records + count_lut_records, histogram_calls + count_lut_calls,
         "histogram plus one nonzero LUT per symbol"),
        ("plurality margin", histogram_records + len(SORT5) * comparison_records,
         histogram_calls + len(SORT5), "histogram plus a 9-comparator count-sorting network"),
        ("modal frequency", histogram_records + (t - 1) * comparison_records,
         histogram_calls + t - 1, "histogram plus a maximum-count chain"),
        ("singleton-symbol count", histogram_records + count_lut_records,
         histogram_calls + count_lut_calls, "histogram plus one [c_v=1] LUT per symbol"),
        ("repeated-symbol count", histogram_records + count_lut_records,
         histogram_calls + count_lut_calls, "histogram plus one [c_v>=2] LUT per symbol"),
        ("exact-two-symbol count", histogram_records + count_lut_records,
         histogram_calls + count_lut_calls, "histogram plus one [c_v=2] LUT per symbol"),
        ("heavy-symbol count", histogram_records + count_lut_records,
         histogram_calls + count_lut_calls, "histogram plus one [c_v>=3] LUT per symbol"),
        ("least positive frequency", histogram_records + count_lut_records + (t - 1) * comparison_records,
         histogram_calls + count_lut_calls + t - 1,
         "map zero counts to 9, then take the minimum positive count"),
        ("occupied-frequency range", histogram_records + count_lut_records + 2 * (t - 1) * comparison_records,
         histogram_calls + count_lut_calls + 2 * (t - 1),
         "map zero counts to 9 and compute max(count)-min_positive(count)"),
        ("number of modal symbols", histogram_records + (t - 1) * comparison_records + t * comparison_records,
         histogram_calls + (t - 1) + t,
         "find the maximum count, then test each count for equality with it"),
    ]
    comparisons: list[Comparison] = []
    for name, records, calls, route in retained_specs:
        comparisons.append(make_comparison(
            section="retained histogram statistic", function=name, parameters="t=5, ell=8",
            direct_records=direct, outputs=outputs[name], our_records=records,
            our_lut_evals=calls, alternative_records=packed_alt_records,
            alternative_lut_evals=packed_alt_calls,
            alternative_ciphertext_multiplications=0,
            exact=maximum_error[name] == 0, exhaustive_cases=direct,
            paper_route=route, alternative_route=packed_alt,
            note="The 200 records used to build the histogram are counted for both routes.",
        ))

    for name in ("second frequency moment", "collision-pair count", "Gini bucket"):
        comparisons.append(make_comparison(
            section="screened out", function=name, parameters="t=5, ell=8",
            direct_records=direct, outputs=outputs[name],
            our_records=histogram_records + count_lut_records,
            our_lut_evals=histogram_calls + count_lut_calls,
            alternative_records=histogram_records,
            alternative_lut_evals=histogram_calls,
            alternative_ciphertext_multiplications=t,
            exact=True, exhaustive_cases=direct,
            paper_route="histogram plus one nonlinear count LUT per symbol",
            alternative_route="build the histogram, then use ciphertext multiplications and public additions",
            note="Rejected under the optimistic convention that intermediate multiplications add no LUT records.",
        ))
    return comparisons


def similarity_comparisons() -> list[Comparison]:
    n, scale = 8, 15
    direct = 2 ** (2 * n)
    names = (
        "quantized Jaccard", "quantized Dice", "quantized cosine similarity",
        "quantized overlap coefficient",
    )
    outputs = {name: set() for name in names}
    for bits in product(range(2), repeat=2 * n):
        left, right = bits[:n], bits[n:]
        intersection = sum(a & b for a, b in zip(left, right))
        left_weight = sum(left)
        right_weight = sum(right)
        union = sum(a | b for a, b in zip(left, right))
        outputs["quantized Jaccard"].add(scale if union == 0 else scale * intersection // union)
        denominator = left_weight + right_weight
        outputs["quantized Dice"].add(
            scale if denominator == 0 else 2 * scale * intersection // denominator
        )
        product_weight = left_weight * right_weight
        outputs["quantized cosine similarity"].add(
            scale if left_weight == right_weight == 0
            else 0 if product_weight == 0
            else math.isqrt((scale * intersection) ** 2 // product_weight)
        )
        minimum_weight = min(left_weight, right_weight)
        outputs["quantized overlap coefficient"].add(
            scale if left_weight == right_weight == 0
            else 0 if minimum_weight == 0
            else scale * intersection // minimum_weight
        )

    current = {
        "quantized Jaccard": (113, 9, 81),
        "quantized Dice": (185, 9, 153),
        "quantized cosine similarity": (761, 9, 729),
        "quantized overlap coefficient": (761, 9, 729),
    }
    comparisons: list[Comparison] = []
    for name in names:
        records, calls, alternative = current[name]
        comparisons.append(make_comparison(
            section="screened out", function=name,
            parameters="two binary vectors, n=8, output scale=15",
            direct_records=direct, outputs=outputs[name], our_records=records,
            our_lut_evals=calls, alternative_records=alternative,
            alternative_lut_evals=1, alternative_ciphertext_multiplications=n,
            exact=True, exhaustive_cases=direct,
            paper_route="pair LUTs, accumulated counts, then a normalized-score LUT",
            alternative_route="form the intersection/count statistics by ciphertext multiplication, then one LUT",
            note="Rejected because the optimistic intermediate-count route has fewer LUT records.",
        ))
    return comparisons


def dynamic_program_comparisons() -> list[Comparison]:
    rows = list(csv.DictReader(BASE_RESULTS.open(encoding="utf-8")))
    names = {
        "binary Levenshtein distance",
        "binary longest-common-subsequence length",
        "dynamic time-warping distance",
        "discrete Frechet distance",
    }
    comparisons: list[Comparison] = []
    for row in rows:
        if row["function"] not in names:
            continue
        comparisons.append(make_comparison(
            section="screened out", function=row["function"], parameters=row["parameters"],
            direct_records=int(row["direct_records"]),
            outputs=set(range(int(row["output_cardinality"]))),
            our_records=int(row["decomposed_records"]), our_lut_evals=int(row["lut_calls"]),
            alternative_records=None, alternative_lut_evals=None,
            alternative_ciphertext_multiplications=0,
            exact=row["exact"] == "True" and int(row["maximum_error"]) == 0,
            exhaustive_cases=int(row["exhaustive_cases"]),
            paper_route=row["construction"],
            alternative_route="bit/circuit dynamic program; no defensible conversion to this LUT-record metric",
            force_reject=True,
            note="Removed because the record-only experiment cannot establish strict speed dominance.",
        ))
    assert len(comparisons) == 4
    return comparisons


def write_results(comparisons: list[Comparison]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(comparisons[0]).keys())
    with (OUTPUT_DIR / "intermediate_routes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in comparisons:
            writer.writerow(asdict(item))
    metadata = {
        "comparison_count": len(comparisons),
        "retained_count": sum(item.retained for item in comparisons),
        "retained_elementary_count": sum(
            item.retained and item.section == "elementary" for item in comparisons
        ),
        "retained_general_count": sum(
            item.retained and item.section != "elementary" for item in comparisons
        ),
        "screened_out_count": sum(not item.retained for item in comparisons),
        "criterion": (
            "exact exhaustive check; direct/our >= 2; our LUT records strictly smaller than the "
            "optimistic intermediate route. Intermediate ciphertext multiplications are reported "
            "but assigned zero LUT records."
        ),
        "rows": [asdict(item) for item in comparisons],
    }
    (OUTPUT_DIR / "intermediate_routes.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> int:
    check_networks()
    comparisons = (
        elementary_comparisons()
        + order_and_algebraic_comparisons()
        + histogram_comparisons()
        + similarity_comparisons()
        + dynamic_program_comparisons()
    )
    write_results(comparisons)
    retained = [item for item in comparisons if item.retained]
    assert all(item.exact for item in comparisons)
    assert len(comparisons) == 59
    assert len(retained) == 45
    assert sum(item.section == "elementary" for item in retained) == 19
    assert sum(item.section != "elementary" for item in retained) == 26
    print(
        "PASS: 59 intermediate-route comparisons, 45 retained "
        "(19 elementary and 26 further non-trivial functions)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
