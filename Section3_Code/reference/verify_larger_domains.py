#!/usr/bin/env python3
"""Independent exhaustive check for the t=32 and t=64 Algorithm 1 runners."""

import argparse
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext


BASE = Decimal(2)
SCALES = {32: Decimal(44), 64: Decimal(89)}


def log2(value: int) -> Decimal:
    return Decimal(value).ln() / BASE.ln()


def scaled_log2(value: int, scale: Decimal) -> Decimal:
    if value > 0 and value & (value - 1) == 0:
        return scale * (value.bit_length() - 1)
    return scale * log2(value)


def ceil_log(value: int, scale: Decimal) -> int:
    if value == 0:
        return -1
    return int(scaled_log2(value, scale).to_integral_value(rounding=ROUND_CEILING))


def floor_log(value: int, scale: Decimal) -> int:
    return int(scaled_log2(value, scale).to_integral_value(rounding=ROUND_FLOOR))


def verify(t: int) -> None:
    scale = SCALES[t]
    cases = 0
    deltas = set()
    with localcontext() as context:
        context.prec = 100
        for dividend in range(t):
            for divisor in range(1, t):
                delta = ceil_log(dividend, scale) - floor_log(divisor, scale)
                actual = sum(delta >= ceil_log(level, scale) for level in range(1, t))
                expected = dividend // divisor
                assert actual == expected, (dividend, divisor, delta, actual, expected)
                deltas.add(delta)
                cases += 1
    print(
        "REFERENCE_PASS,"
        f"t={t},M={scale},cases={cases},reachable_deltas={len(deltas)},"
        f"delta_min={min(deltas)},delta_max={max(deltas)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--t", type=int, choices=sorted(SCALES), required=True)
    args = parser.parse_args()
    verify(args.t)


if __name__ == "__main__":
    main()
