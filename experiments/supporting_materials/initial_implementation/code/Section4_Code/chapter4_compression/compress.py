#!/usr/bin/env python3
"""Small-span additive representations with exhaustive verification."""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


Point = tuple[int, ...]
Target = Callable[[Point], int]
Representation = list[list[int]]


@dataclass(frozen=True)
class VerificationReport:
    valid: bool
    span: int
    minimum_sum: int
    maximum_sum: int
    distinct_sums: int
    outer_table: dict[int, int]
    conflict: tuple[Point, int, int] | None = None


@dataclass(frozen=True)
class SymmetricAnnealTrace:
    """Audit record for the deterministic symmetric simulated-annealing search."""

    seed: int
    iterations: int
    restarts: int
    iterations_executed: int
    restarts_executed: int
    max_score: int
    accepted_moves: int
    valid_candidates: int
    initial_rows: tuple[tuple[int, ...], ...]
    improvements: tuple[tuple[int, int, int, tuple[int, ...]], ...]


def all_points(ell: int, t: int) -> list[Point]:
    return list(itertools.product(range(t), repeat=ell))


def additive_sum(representation: Representation, point: Point) -> int:
    return sum(representation[index][value] for index, value in enumerate(point))


def verify(
    representation: Representation,
    t: int,
    target: Target,
    points: Sequence[Point] | None = None,
) -> VerificationReport:
    ell = len(representation)
    if any(len(row) != t for row in representation):
        raise ValueError("every inner table must contain t entries")
    if any(value < 0 for row in representation for value in row):
        return VerificationReport(False, 0, 0, 0, 0, {}, None)
    if points is None:
        points = all_points(ell, t)

    outer: dict[int, int] = {}
    first_point: dict[int, Point] = {}
    minimum = math.inf
    maximum = -math.inf
    for point in points:
        total = additive_sum(representation, point)
        output = target(point)
        minimum = min(minimum, total)
        maximum = max(maximum, total)
        if total in outer and outer[total] != output:
            return VerificationReport(
                False,
                int(maximum - minimum),
                int(minimum),
                int(maximum),
                len(outer),
                outer,
                (point, outer[total], output),
            )
        outer[total] = output
        first_point.setdefault(total, point)

    return VerificationReport(
        True,
        int(maximum - minimum),
        int(minimum),
        int(maximum),
        len(outer),
        dict(sorted(outer.items())),
    )


def base_encoding(ell: int, t: int) -> Representation:
    return [[value * (t**index) for value in range(t)] for index in range(ell)]


def indicator_representation(ell: int, t: int, symbols: Iterable[int]) -> Representation:
    selected = set(symbols)
    return [[int(value in selected) for value in range(t)] for _ in range(ell)]


def hamming_distance_representation(t: int, template: Sequence[int]) -> Representation:
    return [[int(value != expected) for value in range(t)] for expected in template]


def weighted_representation(
    t: int, weights: Sequence[int], unary_scores: Sequence[Sequence[int]]
) -> Representation:
    if len(weights) != len(unary_scores):
        raise ValueError("weights and score tables have different lengths")
    result: Representation = []
    for weight, scores in zip(weights, unary_scores):
        if weight < 0 or len(scores) != t or any(score < 0 for score in scores):
            raise ValueError("weights and unary scores must be non-negative")
        result.append([weight * score for score in scores])
    return result


def _same_output_pair(
    generator: random.Random, points: Sequence[Point], outputs: Sequence[int]
) -> tuple[Point, Point] | None:
    by_output: dict[int, list[Point]] = {}
    for point, output in zip(points, outputs):
        by_output.setdefault(output, []).append(point)
    eligible = [group for group in by_output.values() if len(group) >= 2]
    if not eligible:
        return None
    group = generator.choice(eligible)
    return tuple(generator.sample(group, 2))  # type: ignore[return-value]


def _candidate(
    current: Representation,
    generator: random.Random,
    points: Sequence[Point],
    outputs: Sequence[int],
) -> Representation:
    candidate = [row[:] for row in current]
    ell = len(candidate)
    move = generator.choice(("merge", "aggregate", "perturb"))

    if move == "perturb":
        coordinate = generator.randrange(ell)
        value = generator.randrange(len(candidate[coordinate]))
        candidate[coordinate][value] += generator.choice((-2, -1, 1, 2))
        return candidate

    pair = _same_output_pair(generator, points, outputs)
    if pair is None:
        return candidate
    left, right = pair
    differing = [index for index in range(ell) if left[index] != right[index]]
    if not differing:
        return candidate
    coordinate = generator.choice(differing)
    difference = additive_sum(current, right) - additive_sum(current, left)

    if move == "merge":
        if generator.random() < 0.5:
            candidate[coordinate][left[coordinate]] += difference
        else:
            candidate[coordinate][right[coordinate]] -= difference
    elif difference % 2 == 0:
        candidate[coordinate][left[coordinate]] += difference // 2
        candidate[coordinate][right[coordinate]] -= difference // 2
    return candidate


def anneal(
    ell: int,
    t: int,
    target: Target,
    *,
    iterations: int = 10_000,
    seed: int = 20260803,
    initial_temperature: float = 20.0,
    cooling_rate: float = 0.9995,
    reheat_interval: int = 2_000,
    reheat_factor: float = 0.5,
) -> tuple[Representation, VerificationReport]:
    """Search while exhaustively enforcing non-negativity and separation."""
    points = all_points(ell, t)
    outputs = [target(point) for point in points]
    generator = random.Random(seed)

    current = base_encoding(ell, t)
    current_report = verify(current, t, target, points)
    best = [row[:] for row in current]
    best_report = current_report
    temperature = initial_temperature
    stale = 0

    for _ in range(iterations):
        candidate = _candidate(current, generator, points, outputs)
        candidate_report = verify(candidate, t, target, points)
        if not candidate_report.valid:
            stale += 1
        else:
            delta = candidate_report.span - current_report.span
            accept = delta <= 0 or generator.random() < math.exp(-delta / max(temperature, 1e-12))
            if accept:
                current = candidate
                current_report = candidate_report
            if candidate_report.span < best_report.span:
                best = [row[:] for row in candidate]
                best_report = candidate_report
                stale = 0
            else:
                stale += 1

        temperature *= cooling_rate
        if stale >= reheat_interval:
            temperature += (initial_temperature - temperature) * reheat_factor
            stale = 0

    final_report = verify(best, t, target, points)
    if not final_report.valid:
        raise AssertionError("internal error: returned representation is invalid")
    return best, final_report


def _normalise_row(row: Sequence[int]) -> list[int]:
    minimum = min(row)
    return [value - minimum for value in row]


def _symmetric_energy(
    row: Sequence[int],
    points: Sequence[Point],
    outputs: Sequence[int],
    ell: int,
) -> tuple[int, int, bool]:
    """Return (energy, span, valid) for one shared unary inner table.

    Invalid candidates receive a collision penalty.  Unlike ``anneal`` above,
    this permits the search to cross invalid states instead of being trapped at
    the injective base encoding.  The final candidate is still accepted only
    after exhaustive verification by ``verify``.
    """

    bins: dict[int, dict[int, int]] = {}
    for point, output in zip(points, outputs):
        total = sum(row[value] for value in point)
        counts = bins.setdefault(total, {})
        counts[output] = counts.get(output, 0) + 1

    conflicts = sum(sum(counts.values()) - max(counts.values()) for counts in bins.values())
    span = ell * (max(row) - min(row))
    penalty = len(points) * (ell * max(max(row), 1) + 1)
    return conflicts * penalty + span, span, conflicts == 0


def anneal_symmetric(
    ell: int,
    t: int,
    target: Target,
    *,
    iterations: int = 20_000,
    restarts: int = 8,
    seed: int = 20260810,
    max_score: int = 12,
    initial_temperature: float = 100.0,
    cooling_rate: float = 0.9995,
    reheat_interval: int = 2_000,
    target_span: int | None = None,
) -> tuple[Representation, VerificationReport, SymmetricAnnealTrace]:
    """Search a shared unary table for a symmetric multivariate function.

    The restriction ``p_1=...=p_ell`` is natural for symmetric functions such
    as the median.  Every energy evaluation enumerates the complete finite
    domain, and the returned representation is independently checked by
    ``verify``.  A fixed seed makes both the representation and trace
    reproducible.
    """

    if t < 2 or ell < 1 or iterations < 1 or restarts < 1 or max_score < 1:
        raise ValueError("invalid symmetric annealing parameters")

    points = all_points(ell, t)
    outputs = [target(point) for point in points]
    generator = random.Random(seed)
    accepted_moves = 0
    valid_candidates = 0
    initial_rows: list[tuple[int, ...]] = []
    improvements: list[tuple[int, int, int, tuple[int, ...]]] = []
    best_row: list[int] | None = None
    best_span = math.inf
    iterations_executed = 0
    restarts_executed = 0

    for restart in range(restarts):
        restarts_executed += 1
        current = _normalise_row([generator.randrange(max_score + 1) for _ in range(t)])
        current_energy, current_span, current_valid = _symmetric_energy(
            current, points, outputs, ell
        )
        initial_rows.append(tuple(current))
        temperature = initial_temperature
        stale = 0

        if current_valid:
            valid_candidates += 1
            if current_span < best_span:
                best_row = current[:]
                best_span = current_span
                improvements.append((restart, 0, current_span, tuple(current)))

        for iteration in range(1, iterations + 1):
            iterations_executed += 1
            candidate = current[:]
            index = generator.randrange(t)
            candidate[index] = min(
                max_score,
                max(0, candidate[index] + generator.choice((-2, -1, 1, 2))),
            )
            candidate = _normalise_row(candidate)
            candidate_energy, candidate_span, candidate_valid = _symmetric_energy(
                candidate, points, outputs, ell
            )
            delta = candidate_energy - current_energy
            if delta <= 0 or generator.random() < math.exp(-delta / max(temperature, 1e-12)):
                current = candidate
                current_energy = candidate_energy
                current_span = candidate_span
                current_valid = candidate_valid
                accepted_moves += 1

            if current_valid:
                valid_candidates += 1
                if current_span < best_span:
                    best_row = current[:]
                    best_span = current_span
                    improvements.append((restart, iteration, current_span, tuple(current)))
                    stale = 0
                else:
                    stale += 1
            else:
                stale += 1

            temperature *= cooling_rate
            if stale >= reheat_interval:
                temperature = max(temperature, initial_temperature * 0.5)
                stale = 0
            if target_span is not None and best_span <= target_span:
                break

        if target_span is not None and best_span <= target_span:
            break

    if best_row is None:
        raise RuntimeError("simulated annealing did not find a valid symmetric representation")

    representation = [best_row[:] for _ in range(ell)]
    final_report = verify(representation, t, target, points)
    if not final_report.valid:
        raise AssertionError("internal error: symmetric annealing returned an invalid representation")
    trace = SymmetricAnnealTrace(
        seed=seed,
        iterations=iterations,
        restarts=restarts,
        iterations_executed=iterations_executed,
        restarts_executed=restarts_executed,
        max_score=max_score,
        accepted_moves=accepted_moves,
        valid_candidates=valid_candidates,
        initial_rows=tuple(initial_rows),
        improvements=tuple(improvements),
    )
    return representation, final_report, trace
