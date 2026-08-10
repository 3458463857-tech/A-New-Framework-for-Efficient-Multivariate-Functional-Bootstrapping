"""Representative finite multivariate functions used in Section 4."""

from __future__ import annotations

from collections import Counter
from typing import Collection, Sequence


Point = tuple[int, ...]


def mode(point: Point) -> int:
    """Return the smallest mode in case of a tie."""
    counts = Counter(point)
    maximum = max(counts.values())
    return min(value for value, count in counts.items() if count == maximum)


def lower_median(point: Point) -> int:
    ordered = sorted(point)
    return ordered[(len(ordered) - 1) // 2]


def symbol_count(point: Point, symbols: Collection[int]) -> int:
    symbol_set = set(symbols)
    return sum(value in symbol_set for value in point)


def symbol_set_threshold(point: Point, symbols: Collection[int], threshold: int) -> int:
    return int(symbol_count(point, symbols) >= threshold)


def symbol_set_interval(
    point: Point, symbols: Collection[int], lower: int, upper: int
) -> int:
    return int(lower <= symbol_count(point, symbols) <= upper)


def exact_k(point: Point, symbols: Collection[int], target: int) -> int:
    return int(symbol_count(point, symbols) == target)


def hamming_distance(point: Point, public_template: Sequence[int]) -> int:
    if len(point) != len(public_template):
        raise ValueError("point and template lengths differ")
    return sum(left != right for left, right in zip(point, public_template))


def hamming_ball(point: Point, public_template: Sequence[int], radius: int) -> int:
    return int(hamming_distance(point, public_template) <= radius)


def activation_bit(point: Point) -> int:
    """The counterexample used in the manuscript."""
    ell = len(point)
    value = sum(bit << (ell - 1 - index) for index, bit in enumerate(point))
    transformed = ((value * 131 + 17) ^ ((value >> 3) + (value << 5))) % (1 << ell)
    bit_index = ell - 2
    return (transformed >> bit_index) & 1
