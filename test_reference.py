from __future__ import annotations

import sys
import unittest
import csv
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chapter4_compression"))

from compress import (
    anneal,
    anneal_symmetric,
    hamming_distance_representation,
    indicator_representation,
    verify,
)
from functions import hamming_ball, lower_median, mode, symbol_set_interval, symbol_set_threshold


class CompressionTests(unittest.TestCase):
    def test_symbol_interval_explicit_span(self) -> None:
        ell, t, symbols = 6, 4, {1, 3}
        representation = indicator_representation(ell, t, symbols)
        target = lambda point: symbol_set_interval(point, symbols, 2, 4)
        report = verify(representation, t, target)
        self.assertTrue(report.valid)
        self.assertEqual(report.span, ell)

    def test_symbol_threshold_explicit_span(self) -> None:
        ell, t, symbols = 8, 3, {1}
        representation = indicator_representation(ell, t, symbols)
        target = lambda point: symbol_set_threshold(point, symbols, 4)
        report = verify(representation, t, target)
        self.assertTrue(report.valid)
        self.assertEqual(report.span, ell)

    def test_hamming_ball(self) -> None:
        template = (0, 1, 1, 0)
        representation = hamming_distance_representation(2, template)
        target = lambda point: hamming_ball(point, template, 1)
        self.assertTrue(verify(representation, 2, target).valid)

    def test_small_anneal_returns_verified_result(self) -> None:
        representation, report = anneal(3, 3, mode, iterations=200, seed=7)
        self.assertTrue(report.valid)
        self.assertTrue(verify(representation, 3, mode).valid)

    def test_table11_median_anneal_record(self) -> None:
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
        self.assertTrue(report.valid)
        self.assertEqual(report.span, 42)
        self.assertEqual(verify(representation, 3, lower_median).span, 42)
        self.assertEqual(trace.seed, 20260810)

    def test_table11_three_variable_packing(self) -> None:
        records = ROOT / "chapter4_compression" / "records" / "table11_representations.csv"
        cases: dict[str, dict[str, object]] = {}
        with records.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                case = cases.setdefault(
                    row["case_id"],
                    {
                        "t": int(row["t"]),
                        "ell": int(row["ell"]),
                        "rows": {},
                    },
                )
                coordinate = int(row["coordinate"])
                case["rows"].setdefault(coordinate, {})[int(row["input"])] = int(row["score"])

        for case_id, case in cases.items():
            if case_id == "hamming_weight_interval":
                continue
            t = case["t"]
            ell = case["ell"]
            rows = case["rows"]
            self.assertEqual(ell, 6)
            for start in (0, 3):
                for digits in product(range(t), repeat=3):
                    packed = sum(digit * t**index for index, digit in enumerate(digits))
                    self.assertLess(packed, 64)
                    decoded = tuple((packed // t**index) % t for index in range(3))
                    packed_output = sum(rows[start + index][digit] for index, digit in enumerate(decoded))
                    direct_output = sum(rows[start + index][digit] for index, digit in enumerate(digits))
                    self.assertEqual(packed_output, direct_output)
                    self.assertLess(packed_output, 64)


if __name__ == "__main__":
    unittest.main()
