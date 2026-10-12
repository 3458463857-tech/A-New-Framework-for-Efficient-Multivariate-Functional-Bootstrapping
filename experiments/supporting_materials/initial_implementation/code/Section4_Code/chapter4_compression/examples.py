#!/usr/bin/env python3
"""Run small, exactly verified examples from the Section 4 function families."""

from __future__ import annotations

from compress import anneal, hamming_distance_representation, indicator_representation, verify
from functions import hamming_ball, lower_median, mode, symbol_set_interval, symbol_set_threshold


def display(name: str, representation: list[list[int]], report) -> None:
    print(
        f"{name}: PASS; span={report.span}; distinct_sums={report.distinct_sums}; "
        f"range=[{report.minimum_sum},{report.maximum_sum}]; p={representation}"
    )


def main() -> int:
    # Explicit construction: a symbol-set interval depends only on one count.
    ell, t, symbols = 6, 4, {1, 3}
    representation = indicator_representation(ell, t, symbols)
    target = lambda point: symbol_set_interval(point, symbols, 2, 4)
    display("symbol-set interval", representation, verify(representation, t, target))

    # Explicit construction: a symbol-set threshold uses the same inner maps.
    symbols = {0, 2}
    representation = indicator_representation(ell, t, symbols)
    target = lambda point: symbol_set_threshold(point, symbols, 3)
    display("symbol-set threshold", representation, verify(representation, t, target))

    # Explicit construction: distance to a public template is a sum of mismatches.
    template = (0, 1, 1, 0, 1, 0, 0, 1)
    representation = hamming_distance_representation(2, template)
    target = lambda point: hamming_ball(point, template, 2)
    display("Hamming ball", representation, verify(representation, 2, target))

    # Binary mode and lower median are both functions of the Hamming weight.
    representation = indicator_representation(10, 2, {1})
    display("binary mode", representation, verify(representation, 2, mode))
    display("binary lower median", representation, verify(representation, 2, lower_median))

    # A small non-binary example exercises the heuristic and exhaustive checker.
    representation, report = anneal(3, 3, mode, iterations=2_000, seed=20260803)
    display("ternary mode (annealed)", representation, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
