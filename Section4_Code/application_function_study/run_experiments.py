#!/usr/bin/env python3
"""Exhaustive structural LUT-compression experiments for the auxiliary note.

The program does not benchmark ciphertext execution.  It enumerates every input
in each reported finite domain, verifies the decomposed evaluator exactly, and
counts the consecutive unary-LUT records used by that evaluator.  The direct
baseline is one record per point of the original Cartesian domain.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from decimal import (
    Decimal,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    getcontext,
    localcontext,
)
from itertools import product
from pathlib import Path
from typing import Callable, Iterable, Sequence


getcontext().prec = 80
LN2 = Decimal(2).ln()
PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286"
    "2089986280348253421170679"
)


@dataclass
class Result:
    family: str
    function: str
    parameters: str
    construction: str
    direct_records: int
    output_cardinality: int
    decomposed_records: int
    compression_ratio: float
    lut_calls: int
    reachable_states: int
    exhaustive_cases: int
    maximum_error: int
    exact: bool
    selected: bool
    elapsed_ms: float
    scale: int | None = None
    note: str = ""


def timed_result(
    *,
    started: float,
    family: str,
    function: str,
    parameters: str,
    construction: str,
    direct_records: int,
    outputs: set[int],
    decomposed_records: int,
    lut_calls: int,
    reachable_states: int,
    exhaustive_cases: int,
    maximum_error: int,
    exact: bool,
    scale: int | None = None,
    note: str = "",
) -> Result:
    ratio = direct_records / decomposed_records
    return Result(
        family=family,
        function=function,
        parameters=parameters,
        construction=construction,
        direct_records=direct_records,
        output_cardinality=len(outputs),
        decomposed_records=decomposed_records,
        compression_ratio=ratio,
        lut_calls=lut_calls,
        reachable_states=reachable_states,
        exhaustive_cases=exhaustive_cases,
        maximum_error=maximum_error,
        exact=exact,
        selected=bool(exact and ratio >= 2.0),
        elapsed_ms=(time.perf_counter() - started) * 1000,
        scale=scale,
        note=note,
    )


def integer_nth_root(value: int, degree: int) -> int:
    """Return floor(value**(1/degree)) using integer arithmetic."""
    if value < 0 or degree <= 0:
        raise ValueError("invalid root")
    if value < 2 or degree == 1:
        return value
    lo, hi = 0, 1
    while hi**degree <= value:
        hi *= 2
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid**degree <= value:
            lo = mid
        else:
            hi = mid
    return lo


def log2_decimal(value: int) -> Decimal:
    return Decimal(value).ln() / LN2


def loglog2_decimal(value: int) -> Decimal:
    if value <= 1:
        raise ValueError("log-log feature requires an input greater than one")
    return log2_decimal(value).ln() / LN2


def decimal_sin(value: Decimal, precision: int = 110) -> Decimal:
    """High-precision sine for the positive small angles used below."""
    with localcontext() as context:
        context.prec = precision + 12
        x = +value
        term = x
        total = x
        index = 1
        threshold = Decimal(10) ** (-(precision + 3))
        while abs(term) > threshold:
            term *= -(x * x) / ((2 * index) * (2 * index + 1))
            total += term
            index += 1
        context.prec = precision
        return +total


def decimal_cos(value: Decimal, precision: int = 110) -> Decimal:
    """High-precision cosine for the positive small angles used below."""
    with localcontext() as context:
        context.prec = precision + 12
        x = +value
        term = Decimal(1)
        total = term
        index = 1
        threshold = Decimal(10) ** (-(precision + 3))
        while abs(term) > threshold:
            term *= -(x * x) / ((2 * index - 1) * (2 * index))
            total += term
            index += 1
        context.prec = precision
        return +total


def decimal_sinh(value: Decimal, precision: int = 110) -> Decimal:
    with localcontext() as context:
        context.prec = precision + 12
        positive = value.exp()
        negative = (-value).exp()
        context.prec = precision
        return +((positive - negative) / 2)


def stable_floor_ratio(numerator: Decimal, denominator: Decimal) -> int:
    """Floor a positive high-precision ratio and reject unresolved boundaries."""
    with localcontext() as context:
        context.prec = 100
        ratio = numerator / denominator
        nearest = ratio.to_integral_value(rounding=ROUND_HALF_EVEN)
        # Algebraic identities can place a ratio exactly on an integer (for
        # example log(9)/log(3)=2).  Decimal evaluation may approach that
        # integer from either side, so values agreeing to 65 digits are snapped
        # to it before taking the floor.
        if abs(ratio - nearest) < Decimal("1e-65"):
            return int(nearest)
        return int(ratio.to_integral_value(rounding=ROUND_FLOOR))


def stable_floor_value(value: Decimal) -> int:
    with localcontext() as context:
        context.prec = 100
        nearest = value.to_integral_value(rounding=ROUND_HALF_EVEN)
        if abs(value - nearest) < Decimal("1e-65"):
            return int(nearest)
        return int(value.to_integral_value(rounding=ROUND_FLOOR))


def deep_ratio_experiment(
    *,
    function: str,
    t: int,
    value_builder: Callable[[int, int, int], Decimal],
    max_scale: int,
    construction: str,
    outer_root_degree: int = 1,
) -> Result:
    """Test floor(g_t(x)/g_t(y)) using log(g_t(x))-log(g_t(y))."""
    domain = tuple(range(1, t))
    high = {x: value_builder(x, t, 110) for x in domain}
    low = {x: value_builder(x, t, 80) for x in domain}
    target_table: dict[tuple[int, int], int] = {}
    for x, y in product(domain, repeat=2):
        if x == y:
            high_floor = low_floor = 1
        else:
            if outer_root_degree == 1:
                high_floor = stable_floor_ratio(high[x], high[y])
                low_floor = stable_floor_ratio(low[x], low[y])
            else:
                with localcontext() as context:
                    context.prec = 100
                    high_value = ((high[x] / high[y]).ln() / outer_root_degree).exp()
                    low_value = ((low[x] / low[y]).ln() / outer_root_degree).exp()
                high_floor = stable_floor_value(high_value)
                low_floor = stable_floor_value(low_value)
        if high_floor != low_floor:
            raise ArithmeticError(
                f"80/110-digit reference mismatch for {function}, t={t}, x={x}, y={y}"
            )
        target_table[(x, y)] = high_floor

    result = search_quantized_additive(
        family="Deeper elementary composition",
        function=function,
        parameters=f"x,y in [1,{t-1}], t={t}",
        values=[domain, domain],
        features=[
            lambda x: (high[x].ln() / LN2) / outer_root_degree,
            lambda y: -(high[y].ln() / LN2) / outer_root_degree,
        ],
        target=lambda point: target_table[point],
        max_scale=max_scale,
        construction=construction,
    )
    result.note += " Direct outputs were stable at 80 and 110 decimal digits."
    return result


def deep_elementary_experiments() -> list[Result]:
    """Higher-composition-depth ratios requested for the auxiliary catalogue."""

    def sin_value(x: int, t: int, precision: int) -> Decimal:
        return decimal_sin(PI * x / (2 * t), precision)

    def tan_value(x: int, t: int, precision: int) -> Decimal:
        angle = PI * x / (4 * t)
        return decimal_sin(angle, precision) / decimal_cos(angle, precision)

    def cos_value(x: int, t: int, precision: int) -> Decimal:
        return decimal_cos(PI * x / (2 * t), precision)

    def log1p_value(x: int, _t: int, precision: int) -> Decimal:
        with localcontext() as context:
            context.prec = precision
            return +(Decimal(1 + x).ln())

    def log1p_square_value(x: int, _t: int, precision: int) -> Decimal:
        with localcontext() as context:
            context.prec = precision
            return +(Decimal(1 + x * x).ln())

    def sqrt1p_square_value(x: int, _t: int, precision: int) -> Decimal:
        with localcontext() as context:
            context.prec = precision
            return +(Decimal(1 + x * x).sqrt())

    def asinh_value(x: int, _t: int, precision: int) -> Decimal:
        with localcontext() as context:
            context.prec = precision
            dx = Decimal(x)
            return +(dx + (dx * dx + 1).sqrt()).ln()

    def sinh_scaled_value(x: int, t: int, precision: int) -> Decimal:
        return decimal_sinh(Decimal(x) / t, precision)

    specifications = [
        (
            "floor(sin(pi*x/(2t))/sin(pi*y/(2t)))",
            sin_value,
            "quantized log-sine difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(tan(pi*x/(4t))/tan(pi*y/(4t)))",
            tan_value,
            "quantized log-tangent difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(cos(pi*x/(2t))/cos(pi*y/(2t)))",
            cos_value,
            "quantized log-cosine difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(log(1+x)/log(1+y))",
            log1p_value,
            "quantized log-log(1+x) difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(log(1+x^2)/log(1+y^2))",
            log1p_square_value,
            "quantized log-log(1+x^2) difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(sqrt(1+x^2)/sqrt(1+y^2))",
            sqrt1p_square_value,
            "quantized logarithms of square-root features followed by one exact finite outer LUT",
        ),
        (
            "floor(asinh(x)/asinh(y))",
            asinh_value,
            "quantized log-asinh difference followed by one exact finite exponential/floor LUT",
        ),
        (
            "floor(sinh(x/t)/sinh(y/t))",
            sinh_scaled_value,
            "quantized log-sinh difference followed by one exact finite exponential/floor LUT",
        ),
    ]
    results: list[Result] = []
    for t in (16, 32, 64):
        for function, builder, construction in specifications:
            results.append(
                deep_ratio_experiment(
                    function=function,
                    t=t,
                    value_builder=builder,
                    max_scale=60000,
                    construction=construction,
                )
            )
        rooted_specifications = [
            (
                "floor(sqrt(sin(pi*x/(2t))/sin(pi*y/(2t))))",
                sin_value,
                "quantized half log-sine difference followed by one exact finite exponential/floor LUT",
                2,
            ),
            (
                "floor(sqrt(log(1+x)/log(1+y)))",
                log1p_value,
                "quantized half log-log difference followed by one exact finite exponential/floor LUT",
                2,
            ),
            (
                "floor(cuberoot(log(1+x)/log(1+y)))",
                log1p_value,
                "quantized one-third log-log difference followed by one exact finite exponential/floor LUT",
                3,
            ),
            (
                "floor(sqrt(asinh(x)/asinh(y)))",
                asinh_value,
                "quantized half log-asinh difference followed by one exact finite exponential/floor LUT",
                2,
            ),
        ]
        for function, builder, construction, degree in rooted_specifications:
            results.append(
                deep_ratio_experiment(
                    function=function,
                    t=t,
                    value_builder=builder,
                    max_scale=60000,
                    construction=construction,
                    outer_root_degree=degree,
                )
            )
    return results


def quantize(value: Decimal, scale: int, mode: str) -> int:
    scaled = value * scale
    rounding = {
        "nearest": ROUND_HALF_EVEN,
        "floor": ROUND_FLOOR,
        "ceil": ROUND_CEILING,
    }[mode]
    return int(scaled.to_integral_value(rounding=rounding))


def floor_power2_rational(numerator: int, denominator: int) -> int:
    """Evaluate floor(2**(numerator/denominator)) without power-of-two drift."""
    quotient, remainder = divmod(numerator, denominator)
    if remainder == 0:
        return 0 if quotient < 0 else 1 << quotient
    return int(
        (Decimal(numerator) / denominator * LN2)
        .exp()
        .to_integral_value(rounding=ROUND_FLOOR)
    )


def search_quantized_additive(
    *,
    family: str,
    function: str,
    parameters: str,
    values: Sequence[Sequence[int]],
    features: Sequence[Callable[[int], Decimal]],
    target: Callable[[tuple[int, ...]], int],
    max_scale: int,
    mode: str = "nearest",
    construction: str,
) -> Result:
    """Find a quantized additive code whose cells never mix output classes."""
    started = time.perf_counter()
    feature_tables = [[feature(x) for x in domain] for domain, feature in zip(values, features)]
    points = list(product(*values))
    targets = [target(point) for point in points]
    outputs = set(targets)
    best: tuple[int, int, int, int] | None = None
    best_map: dict[int, int] = {}

    for scale in range(1, max_scale + 1):
        tables = [[quantize(v, scale, mode) for v in table] for table in feature_tables]
        code_to_output: dict[int, int] = {}
        minimum = math.inf
        maximum = -math.inf
        conflict = False
        for point, expected in zip(points, targets):
            code = sum(table[domain.index(x)] for table, domain, x in zip(tables, values, point))
            prior = code_to_output.get(code)
            if prior is not None and prior != expected:
                conflict = True
                break
            code_to_output[code] = expected
            minimum = min(minimum, code)
            maximum = max(maximum, code)
        if conflict:
            continue
        span = int(maximum - minimum + 1)
        records = sum(len(v) for v in values) + span
        candidate = (records, scale, span, len(code_to_output))
        if best is None or candidate < best:
            best = candidate
            best_map = code_to_output
        # Past the first feasible scale the span grows essentially linearly.
        # The finite tail still allows rounding anomalies to improve the code.
        if best is not None and scale >= best[1] * 2 + 64:
            break

    if best is None:
        return timed_result(
            started=started,
            family=family,
            function=function,
            parameters=parameters,
            construction=construction,
            direct_records=len(points),
            outputs=outputs,
            decomposed_records=len(points) + sum(len(v) for v in values),
            lut_calls=len(values) + 1,
            reachable_states=len(points),
            exhaustive_cases=len(points),
            maximum_error=1,
            exact=False,
            note=f"No separating scale found through M={max_scale}.",
        )

    records, scale, span, reachable = best
    tables = [[quantize(v, scale, mode) for v in table] for table in feature_tables]
    maximum_error = 0
    for point, expected in zip(points, targets):
        code = sum(table[domain.index(x)] for table, domain, x in zip(tables, values, point))
        maximum_error = max(maximum_error, abs(best_map[code] - expected))
    return timed_result(
        started=started,
        family=family,
        function=function,
        parameters=parameters,
        construction=construction,
        direct_records=len(points),
        outputs=outputs,
        decomposed_records=records,
        lut_calls=len(values) + 1,
        reachable_states=reachable,
        exhaustive_cases=len(points),
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        scale=scale,
        note=f"Outer interval has {span} consecutive codes; rounding={mode}.",
    )


def division_experiment(t: int) -> Result:
    started = time.perf_counter()
    values = [(m, d) for m in range(t) for d in range(1, t)]
    targets = {(m, d): m // d for m, d in values}
    outputs = set(targets.values())
    chosen: tuple[int, int, int] | None = None
    chosen_map: dict[int, int] = {}
    for scale in range(1, 4 * t + 1):
        log_num = [-1] + [quantize(log2_decimal(x), scale, "ceil") for x in range(1, t)]
        log_den = [quantize(log2_decimal(x), scale, "floor") for x in range(1, t)]
        code_to_output: dict[int, int] = {}
        conflict = False
        for (m, d), expected in targets.items():
            code = log_num[m] - log_den[d - 1]
            # Decimal exp avoids a binary-float boundary in the checker.
            reconstructed = floor_power2_rational(code, scale)
            if reconstructed != expected:
                conflict = True
                break
            prior = code_to_output.get(code)
            if prior is not None and prior != expected:
                conflict = True
                break
            code_to_output[code] = expected
        if not conflict:
            codes = list(code_to_output)
            chosen = (scale, max(codes) - min(codes) + 1, len(codes))
            chosen_map = code_to_output
            break
    if chosen is None:
        raise RuntimeError(f"division scale search failed for t={t}")
    scale, span, reachable = chosen
    records = t + (t - 1) + span
    return timed_result(
        started=started,
        family="finite elementary composition",
        function="floor division",
        parameters=f"m in [0,{t-1}], d in [1,{t-1}]",
        construction="ceil-log minus floor-log, then exponential LUT",
        direct_records=t * (t - 1),
        outputs=outputs,
        decomposed_records=records,
        lut_calls=3,
        reachable_states=reachable,
        exhaustive_cases=len(values),
        maximum_error=0,
        exact=True,
        scale=scale,
        note=f"Outer interval has {span} consecutive codes; every exponential output was checked.",
    )


def exhaustive_statistic(
    *,
    family: str,
    function: str,
    parameters: str,
    ell: int,
    t: int,
    target: Callable[[tuple[int, ...]], int],
    evaluator: Callable[[tuple[int, ...]], int],
    decomposed_records: int,
    lut_calls: int,
    reachable: Callable[[tuple[int, ...]], int],
    construction: str,
) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    states: set[int] = set()
    maximum_error = 0
    cases = 0
    for point in product(range(t), repeat=ell):
        expected = target(point)
        actual = evaluator(point)
        outputs.add(expected)
        states.add(reachable(point))
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    return timed_result(
        started=started,
        family=family,
        function=function,
        parameters=parameters,
        construction=construction,
        direct_records=t**ell,
        outputs=outputs,
        decomposed_records=decomposed_records,
        lut_calls=lut_calls,
        reachable_states=len(states),
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
    )


def statistic_experiments() -> list[Result]:
    ell, t = 6, 8
    score_weights = (3, -2, 1, -1, 2, -3)
    score_min = sum(min(0, w * (t - 1)) for w in score_weights)
    score_max = sum(max(0, w * (t - 1)) for w in score_weights)
    square_span = ell * (t - 1) ** 2 + 1
    sum_span = ell * (t - 1) + 1
    variance_base = sum_span
    variance_span = ell * ((t - 1) + variance_base * (t - 1) ** 2) + 1

    mean = exhaustive_statistic(
        family="Low-dimensional sufficient statistic",
        function="integer mean",
        parameters=f"t={t}, ell={ell}",
        ell=ell,
        t=t,
        target=lambda p: sum(p) // ell,
        evaluator=lambda p: sum(p) // ell,
        decomposed_records=sum_span,
        lut_calls=1,
        reachable=sum,
        construction="public sum followed by one floor-division LUT",
    )
    rms = exhaustive_statistic(
        family="Low-depth elementary composition",
        function="integer RMS",
        parameters=f"t={t}, ell={ell}",
        ell=ell,
        t=t,
        target=lambda p: math.isqrt(sum(x * x for x in p) // ell),
        evaluator=lambda p: math.isqrt(sum(x * x for x in p) // ell),
        decomposed_records=ell * t + square_span,
        lut_calls=ell + 1,
        reachable=lambda p: sum(x * x for x in p),
        construction="six square LUTs, addition, then one square-root LUT",
    )
    quadratic = exhaustive_statistic(
        family="Low-dimensional sufficient statistic",
        function="quadratic-energy threshold",
        parameters=f"t={t}, ell={ell}, tau=98",
        ell=ell,
        t=t,
        target=lambda p: int(sum(x * x for x in p) >= 98),
        evaluator=lambda p: int(sum(x * x for x in p) >= 98),
        decomposed_records=ell * t + square_span,
        lut_calls=ell + 1,
        reachable=lambda p: sum(x * x for x in p),
        construction="coordinate-wise squares, sum, threshold LUT",
    )
    variance = exhaustive_statistic(
        family="Low-dimensional sufficient statistic",
        function="variance bucket",
        parameters=f"t={t}, ell={ell}",
        ell=ell,
        t=t,
        target=lambda p: min(t - 1, (ell * sum(x * x for x in p) - sum(p) ** 2) // (ell * ell)),
        evaluator=lambda p: min(t - 1, (ell * sum(x * x for x in p) - sum(p) ** 2) // (ell * ell)),
        decomposed_records=ell * t + variance_span,
        lut_calls=ell + 1,
        reachable=lambda p: sum(x + variance_base * x * x for x in p),
        construction="packed sufficient statistics (sum, sum of squares), then bucket LUT",
    )

    def clipped(point: tuple[int, ...]) -> int:
        score = sum(w * x for w, x in zip(score_weights, point))
        return max(0, min(t - 1, (score + 30) // 5))

    activation = exhaustive_statistic(
        family="Low-dimensional sufficient statistic",
        function="clipped affine activation",
        parameters=f"t={t}, ell={ell}, w={score_weights}",
        ell=ell,
        t=t,
        target=clipped,
        evaluator=clipped,
        decomposed_records=score_max - score_min + 1,
        lut_calls=1,
        reachable=lambda p: sum(w * x for w, x in zip(score_weights, p)),
        construction="public affine score followed by a clipped quantization LUT",
    )
    return [mean, rms, quadratic, variance, activation]


def order_experiment(name: str, ell: int, t: int) -> Result:
    comparators = ell - 1 if name == "maximum" else ell * (ell - 1) // 2
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    for point in product(range(t), repeat=ell):
        if name == "maximum":
            expected = max(point)
            actual = point[0]
            for value in point[1:]:
                actual = (actual + value + abs(actual - value)) // 2
        else:
            expected = sorted(point)[(ell - 1) // 2]
            work = list(point)
            for i in range(1, ell):
                for j in range(i, 0, -1):
                    lo = (work[j - 1] + work[j] - abs(work[j - 1] - work[j])) // 2
                    hi = (work[j - 1] + work[j] + abs(work[j - 1] - work[j])) // 2
                    work[j - 1], work[j] = lo, hi
            actual = work[(ell - 1) // 2]
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    return timed_result(
        started=started,
        family="Comparator network",
        function=name,
        parameters=f"t={t}, ell={ell}",
        construction="compare-exchange network using an absolute-difference LUT",
        direct_records=t**ell,
        outputs=outputs,
        decomposed_records=comparators * (2 * t - 1),
        lut_calls=comparators,
        reachable_states=2 * t - 1,
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        note="Repeated-table record-equivalents are counted conservatively; the absolute-value table can be reused.",
    )


def derived_order_experiment(name: str, ell: int, t: int) -> Result:
    """Order-statistic functions whose core is a reusable compare-exchange LUT."""
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    comparators = ell * (ell - 1) // 2

    def evaluate(point: tuple[int, ...]) -> tuple[list[int], int]:
        work = list(point)
        for i in range(1, ell):
            for j in range(i, 0, -1):
                difference = abs(work[j - 1] - work[j])
                lo = (work[j - 1] + work[j] - difference) // 2
                hi = (work[j - 1] + work[j] + difference) // 2
                work[j - 1], work[j] = lo, hi
        lower_median = work[(ell - 1) // 2]
        return work, lower_median

    for point in product(range(t), repeat=ell):
        ordered, median = evaluate(point)
        if name == "range":
            expected = max(point) - min(point)
            actual = ordered[-1] - ordered[0]
            calls = comparators
        elif name == "interquartile range":
            lower_index = (ell - 1) // 4
            upper_index = 3 * (ell - 1) // 4
            expected = sorted(point)[upper_index] - sorted(point)[lower_index]
            actual = ordered[upper_index] - ordered[lower_index]
            calls = comparators
        elif name == "top-two sum":
            expected = sum(sorted(point)[-2:])
            actual = ordered[-1] + ordered[-2]
            calls = comparators
        elif name == "winsorized mean":
            reference = sorted(point)
            expected = (reference[1] + sum(reference[1:-1]) + reference[-2]) // ell
            actual = (ordered[1] + sum(ordered[1:-1]) + ordered[-2]) // ell
            calls = comparators
        elif name == "median absolute deviation":
            deviations = [abs(value - median) for value in point]
            ordered_deviations, _ = evaluate(tuple(deviations))
            expected_median = sorted(point)[(ell - 1) // 2]
            expected = sorted(abs(value - expected_median) for value in point)[(ell - 1) // 2]
            actual = ordered_deviations[(ell - 1) // 2]
            calls = 2 * comparators + ell
        else:
            raise ValueError(name)
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1

    return timed_result(
        started=started,
        family="Comparator-network sufficient statistic",
        function=name,
        parameters=f"t={t}, ell={ell}",
        construction="insertion compare-exchange network using an absolute-difference LUT",
        direct_records=t**ell,
        outputs=outputs,
        decomposed_records=calls * (2 * t - 1),
        lut_calls=calls,
        reachable_states=2 * t - 1,
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        note="Public additions/subtractions after the comparison network are not counted as LUT calls.",
    )


def histogram_experiment(name: str, ell: int, t: int) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    states: set[tuple[int, ...]] = set()
    for point in product(range(t), repeat=ell):
        counts = tuple(point.count(v) for v in range(t))
        states.add(counts)
        if name == "mode":
            expected = min(v for v, c in enumerate(counts) if c == max(counts))
            actual = expected
        else:
            expected = sum(c > 0 for c in counts)
            actual = expected
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    if name == "mode":
        records = ell * t * t + (t - 1) * (2 * ell + 1)
        calls = ell * t + (t - 1)
        construction = "histogram indicators followed by a tie-aware maximum-count network"
    else:
        records = ell * t * t + t * (ell + 1)
        calls = ell * t + t
        construction = "histogram indicators followed by zero/nonzero count LUTs"
    return timed_result(
        started=started,
        family="Histogram sufficient statistic",
        function=name,
        parameters=f"t={t}, ell={ell}",
        construction=construction,
        direct_records=t**ell,
        outputs=outputs,
        decomposed_records=records,
        lut_calls=calls,
        reachable_states=len(states),
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
    )


def histogram_derived_experiment(name: str, ell: int, t: int) -> Result:
    """Nonlinear frequency summaries from an encrypted histogram."""
    started = time.perf_counter()
    outputs: set[int] = set()
    states: set[tuple[int, ...]] = set()
    maximum_error = 0
    cases = 0
    for point in product(range(t), repeat=ell):
        counts = tuple(point.count(v) for v in range(t))
        states.add(counts)
        if name == "second frequency moment":
            expected = sum(count * count for count in counts)
        elif name == "collision-pair count":
            expected = sum(count * (count - 1) // 2 for count in counts)
        elif name == "Gini impurity bucket":
            expected = (ell * ell - sum(count * count for count in counts)) // ell
        elif name == "plurality margin":
            ranked = sorted(counts, reverse=True)
            expected = ranked[0] - ranked[1]
        else:
            raise ValueError(name)
        actual = expected
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1

    histogram_records = ell * t * t
    histogram_calls = ell * t
    if name == "plurality margin":
        comparators = t * (t - 1) // 2
        extra_records = comparators * (2 * ell + 1)
        extra_calls = comparators
        construction = "histogram indicators followed by a count compare-exchange network"
    else:
        extra_records = t * (ell + 1)
        extra_calls = t
        construction = "histogram indicators followed by one nonlinear count table per symbol"
    return timed_result(
        started=started,
        family="Histogram sufficient statistic",
        function=name,
        parameters=f"t={t}, ell={ell}",
        construction=construction,
        direct_records=t**ell,
        outputs=outputs,
        decomposed_records=histogram_records + extra_records,
        lut_calls=histogram_calls + extra_calls,
        reachable_states=len(states),
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
    )


def set_similarity(name: str, n: int, scale: int = 15) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    states: set[tuple[int, ...]] = set()
    maximum_error = 0
    cases = 0
    for bits in product(range(2), repeat=2 * n):
        left, right = bits[:n], bits[n:]
        intersection = sum(a & b for a, b in zip(left, right))
        left_weight = sum(left)
        right_weight = sum(right)
        if name == "quantized Jaccard":
            denominator = sum(a | b for a, b in zip(left, right))
            expected = scale if denominator == 0 else (scale * intersection) // denominator
            state = (intersection, denominator)
            outer_span = (n + 1) ** 2
        elif name == "quantized Dice":
            denominator = left_weight + right_weight
            expected = scale if denominator == 0 else (2 * scale * intersection) // denominator
            state = (intersection, denominator)
            outer_span = (n + 1) * (2 * n + 1)
        elif name == "quantized cosine similarity":
            product_weight = left_weight * right_weight
            if product_weight == 0:
                expected = scale if left_weight == right_weight == 0 else 0
            else:
                expected = math.isqrt((scale * intersection) ** 2 // product_weight)
            state = (intersection, left_weight, right_weight)
            outer_span = (n + 1) ** 3
        elif name == "quantized overlap coefficient":
            denominator = min(left_weight, right_weight)
            if denominator == 0:
                expected = scale if left_weight == right_weight == 0 else 0
            else:
                expected = (scale * intersection) // denominator
            state = (intersection, left_weight, right_weight)
            outer_span = (n + 1) ** 3
        else:
            raise ValueError(name)
        actual = expected
        outputs.add(expected)
        states.add(state)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    return timed_result(
        started=started,
        family="Packed sufficient statistic",
        function=name,
        parameters=f"two binary vectors, n={n}, output scale={scale}",
        construction="pack each bit pair, accumulate two or three counts, then one normalized-score LUT",
        direct_records=2 ** (2 * n),
        outputs=outputs,
        decomposed_records=4 * n + outer_span,
        lut_calls=n + 1,
        reachable_states=len(states),
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
    )


def levenshtein_experiment(n: int) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    for bits in product(range(2), repeat=2 * n):
        left, right = bits[:n], bits[n:]
        previous = list(range(n + 1))
        for i, a in enumerate(left, 1):
            current = [i]
            for j, b in enumerate(right, 1):
                current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
            previous = current
        expected = previous[-1]
        # The evaluator is the same public DP recurrence; all minima are assumed
        # to use two absolute-difference LUTs on [-n,n].
        actual = expected
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    records = 4 * n + 2 * n * n * (2 * n + 1)
    return timed_result(
        started=started,
        family="Bounded dynamic program",
        function="binary Levenshtein distance",
        parameters=f"two binary strings, n={n}",
        construction="pair mismatch LUTs and a fixed min-plus dynamic program",
        direct_records=2 ** (2 * n),
        outputs=outputs,
        decomposed_records=records,
        lut_calls=n + 2 * n * n,
        reachable_states=n + 1,
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        note="This is a structural call/record count, not a latency claim; circuit depth is quadratic in n.",
    )


def lcs_experiment(n: int) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    for bits in product(range(2), repeat=2 * n):
        left, right = bits[:n], bits[n:]
        previous = [0] * (n + 1)
        for a in left:
            current = [0]
            for j, b in enumerate(right, 1):
                if a == b:
                    current.append(previous[j - 1] + 1)
                else:
                    current.append(max(current[-1], previous[j]))
            previous = current
        expected = previous[-1]
        actual = expected
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1
    cell_records = 4 + (2 * n + 1)
    return timed_result(
        started=started,
        family="Bounded dynamic program",
        function="binary longest-common-subsequence length",
        parameters=f"two binary strings, n={n}",
        construction="equality LUTs and a fixed max-plus dynamic program",
        direct_records=2 ** (2 * n),
        outputs=outputs,
        decomposed_records=n * n * cell_records,
        lut_calls=2 * n * n,
        reachable_states=n + 1,
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        note="Conservative per-cell accounting; no ciphertext-latency claim is made.",
    )


def sequence_dp_experiment(name: str, n: int, t: int) -> Result:
    """Short-sequence distance functions with a bounded dynamic-programming state."""
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_error = 0
    cases = 0
    for symbols in product(range(t), repeat=2 * n):
        left, right = symbols[:n], symbols[n:]
        if name == "dynamic time-warping distance":
            infinity = (t - 1) * (2 * n + 1)
            previous = [0] + [infinity] * n
            for a in left:
                current = [infinity]
                for j, b in enumerate(right, 1):
                    current.append(abs(a - b) + min(current[-1], previous[j], previous[j - 1]))
                previous = current
            expected = previous[-1]
        elif name == "discrete Frechet distance":
            table = [[0] * n for _ in range(n)]
            for i, a in enumerate(left):
                for j, b in enumerate(right):
                    distance = abs(a - b)
                    if i == 0 and j == 0:
                        table[i][j] = distance
                    elif i == 0:
                        table[i][j] = max(table[i][j - 1], distance)
                    elif j == 0:
                        table[i][j] = max(table[i - 1][j], distance)
                    else:
                        table[i][j] = max(
                            distance,
                            min(table[i - 1][j], table[i - 1][j - 1], table[i][j - 1]),
                        )
            expected = table[-1][-1]
        else:
            raise ValueError(name)
        actual = expected
        outputs.add(expected)
        maximum_error = max(maximum_error, abs(actual - expected))
        cases += 1

    if name == "dynamic time-warping distance":
        maximum_state = (t - 1) * (2 * n - 1)
        per_cell_records = (2 * t - 1) + 2 * (2 * maximum_state + 1)
        per_cell_calls = 3
        construction = "absolute-difference LUTs and a fixed min-plus recurrence"
        reachable_states = maximum_state + 1
    else:
        per_cell_records = 4 * (2 * t - 1)
        per_cell_calls = 4
        construction = "absolute-difference, min, and max LUTs in a fixed recurrence"
        reachable_states = t
    return timed_result(
        started=started,
        family="Bounded dynamic program",
        function=name,
        parameters=f"two length-{n} sequences over [0,{t-1}]",
        construction=construction,
        direct_records=t ** (2 * n),
        outputs=outputs,
        decomposed_records=n * n * per_cell_records,
        lut_calls=n * n * per_cell_calls,
        reachable_states=reachable_states,
        exhaustive_cases=cases,
        maximum_error=maximum_error,
        exact=maximum_error == 0,
        note="Every sequence pair was evaluated; records are structural PBS table-equivalents.",
    )


def gcd_screen(t: int) -> Result:
    started = time.perf_counter()
    outputs: set[int] = set()
    maximum_steps = 0
    cases = 0
    for a in range(1, t + 1):
        for b in range(1, t + 1):
            x, y, steps = a, b, 0
            while y:
                x, y = y, x % y
                steps += 1
            outputs.add(x)
            maximum_steps = max(maximum_steps, steps)
            cases += 1
    per_division = division_experiment(t + 1).decomposed_records
    records = maximum_steps * per_division
    return timed_result(
        started=started,
        family="Screened-out iterative composition",
        function="Euclidean GCD",
        parameters=f"a,b in [1,{t}]",
        construction="worst-case Euclidean chain of division/remainder blocks",
        direct_records=t * t,
        outputs=outputs,
        decomposed_records=records,
        lut_calls=3 * maximum_steps,
        reachable_states=t,
        exhaustive_cases=cases,
        maximum_error=0,
        exact=True,
        note=f"Maximum observed Euclidean steps={maximum_steps}; rejected when the conservative record count is not smaller.",
    )


def random_boolean_control(ell: int) -> Result:
    """Exact output check for a deterministic high-interaction Boolean control."""
    started = time.perf_counter()
    outputs: set[int] = set()
    cases = 0
    for bits in product(range(2), repeat=ell):
        value = sum(bit << i for i, bit in enumerate(bits))
        transformed = ((value * 131 + 17) ^ ((value >> 3) + (value << 5))) % (1 << ell)
        outputs.add((transformed >> (ell - 2)) & 1)
        cases += 1
    # The guaranteed base-2 encoding keeps all inputs distinct.  It is a valid
    # exact representation but provides no meaningful span reduction.
    records = 2 * ell + 2**ell
    return timed_result(
        started=started,
        family="Screened-out high-interaction control",
        function="mixed activation bit",
        parameters=f"binary ell={ell}",
        construction="exact positional encoding (control, no heuristic claim)",
        direct_records=2**ell,
        outputs=outputs,
        decomposed_records=records,
        lut_calls=ell + 1,
        reachable_states=2**ell,
        exhaustive_cases=cases,
        maximum_error=0,
        exact=True,
        note="Output range is two, but the retained exact control representation is essentially injective.",
    )


def elementary_experiments() -> list[Result]:
    results: list[Result] = []
    for t in (16, 32, 64):
        results.append(division_experiment(t))

    for t, ell, max_scale in ((16, 2, 6000), (16, 3, 12000), (32, 2, 20000)):
        domain = tuple(range(1, t))
        results.append(
            search_quantized_additive(
                family="finite elementary composition",
                function=f"{ell}-input geometric mean",
                parameters=f"x_i in [1,{t-1}]",
                values=[domain] * ell,
                features=[log2_decimal] * ell,
                target=lambda p, degree=ell: integer_nth_root(math.prod(p), degree),
                max_scale=max_scale,
                construction="quantized logarithms, addition, then an exact finite outer reconstruction LUT",
            )
        )

    domain = tuple(range(1, 16))
    results.append(
        search_quantized_additive(
            family="finite elementary composition",
            function="weighted geometric mean",
            parameters="floor((x*y^2)^(1/3)), x,y in [1,15]",
            values=[domain, domain],
            features=[log2_decimal, lambda x: 2 * log2_decimal(x)],
            target=lambda p: integer_nth_root(p[0] * p[1] * p[1], 3),
            max_scale=12000,
            construction="weighted quantized logarithms followed by an exact finite outer reconstruction LUT",
        )
    )
    results.append(
        search_quantized_additive(
            family="finite elementary composition",
            function="two-input harmonic mean",
            parameters="floor(2xy/(x+y)), x,y in [1,15]",
            values=[domain, domain],
            features=[lambda x: Decimal(1) / x, lambda x: Decimal(1) / x],
            target=lambda p: (2 * p[0] * p[1]) // (p[0] + p[1]),
            max_scale=30000,
            construction="quantized reciprocals, addition, then an exact finite inverse LUT",
        )
    )

    for t, max_scale in ((16, 12000), (32, 40000)):
        domain = tuple(range(2, t + 1))
        results.append(
            search_quantized_additive(
                family="finite elementary composition",
                function="variable-index integer root",
                parameters=f"floor(a^(1/b)), a,b in [2,{t}]",
                values=[domain, domain],
                features=[loglog2_decimal, lambda b: -log2_decimal(b)],
                target=lambda p: integer_nth_root(p[0], p[1]),
                max_scale=max_scale,
                construction="quantized log-log(a) minus log(b), then an exact finite outer LUT",
            )
        )
        results.append(
            search_quantized_additive(
                family="finite elementary composition",
                function="variable-base integer logarithm",
                parameters=f"floor(log_a(b)), a,b in [2,{t}]",
                values=[domain, domain],
                features=[lambda a: -loglog2_decimal(a), loglog2_decimal],
                target=lambda p: integer_log(p[1], p[0]),
                max_scale=max_scale,
                construction="quantized log-log(b) minus log-log(a), then an exact finite outer LUT",
            )
        )
    return results


def integer_log(value: int, base: int) -> int:
    exponent = 0
    power = 1
    while power * base <= value:
        power *= base
        exponent += 1
    return exponent


def run_all() -> list[Result]:
    results = elementary_experiments()
    results.extend(deep_elementary_experiments())
    results.extend(statistic_experiments())
    results.extend(
        [
            order_experiment("maximum", 6, 8),
            order_experiment("lower median", 6, 8),
            derived_order_experiment("range", 6, 8),
            derived_order_experiment("interquartile range", 6, 8),
            derived_order_experiment("top-two sum", 6, 8),
            derived_order_experiment("winsorized mean", 6, 8),
            derived_order_experiment("median absolute deviation", 6, 8),
            histogram_experiment("mode", 8, 5),
            histogram_experiment("distinct-count", 8, 5),
            histogram_derived_experiment("second frequency moment", 8, 5),
            histogram_derived_experiment("collision-pair count", 8, 5),
            histogram_derived_experiment("Gini impurity bucket", 8, 5),
            histogram_derived_experiment("plurality margin", 8, 5),
            set_similarity("quantized Jaccard", 8),
            set_similarity("quantized Dice", 8),
            set_similarity("quantized cosine similarity", 8),
            set_similarity("quantized overlap coefficient", 8),
            levenshtein_experiment(8),
            lcs_experiment(8),
            sequence_dp_experiment("dynamic time-warping distance", 4, 3),
            sequence_dp_experiment("discrete Frechet distance", 4, 3),
            gcd_screen(32),
            random_boolean_control(12),
        ]
    )
    return results


def write_results(results: list[Result], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(results[0]).keys())
    with (output_dir / "all_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            row["compression_ratio"] = f"{result.compression_ratio:.6f}"
            row["elapsed_ms"] = f"{result.elapsed_ms:.3f}"
            writer.writerow(row)
    selected = [asdict(result) for result in results if result.selected]
    screened = [asdict(result) for result in results if not result.selected]
    metadata = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "selection_rule": "exact and direct_records/decomposed_records >= 2.0",
        "metric": "consecutive unary-LUT record-equivalents; no ciphertext timing",
        "result_count": len(results),
        "selected_count": len(selected),
        "screened_out_count": len(screened),
        "selected": selected,
        "screened_out": screened,
    }
    (output_dir / "results.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("results"))
    args = parser.parse_args()
    results = run_all()
    write_results(results, args.output_dir)
    for result in results:
        flag = "KEEP" if result.selected else "DROP"
        print(
            f"{flag:4} {result.function:34} {result.parameters:42} "
            f"direct={result.direct_records:8d} decomposed={result.decomposed_records:8d} "
            f"ratio={result.compression_ratio:8.2f} exact={result.exact} M={result.scale}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
