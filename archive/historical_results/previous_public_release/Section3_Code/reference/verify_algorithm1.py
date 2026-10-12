#!/usr/bin/env python3
"""Independent exhaustive plaintext check for Section 3, Algorithm 1 (t=16)."""

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext


T = 16
BASE = Decimal(2)
M_SCALE = Decimal(22)


def log2(value: int) -> Decimal:
    return Decimal(value).ln() / BASE.ln()


def scaled_log2(value: int) -> Decimal:
    if value > 0 and value & (value - 1) == 0:
        return M_SCALE * (value.bit_length() - 1)
    return M_SCALE * log2(value)


def ceil_log(value: int) -> int:
    if value == 0:
        return -1
    return int(scaled_log2(value).to_integral_value(rounding=ROUND_CEILING))


def floor_log(value: int) -> int:
    return int(scaled_log2(value).to_integral_value(rounding=ROUND_FLOOR))


def outer_from_thresholds(delta: int) -> int:
    return sum(delta >= ceil_log(level) for level in range(1, T))


def main() -> None:
    with localcontext() as context:
        context.prec = 100
        cases = 0
        deltas = set()
        for dividend in range(T):
            for divisor in range(1, T):
                delta = ceil_log(dividend) - floor_log(divisor)
                actual = outer_from_thresholds(delta)
                expected = dividend // divisor
                assert actual == expected, (dividend, divisor, delta, actual, expected)
                assert -86 <= delta <= 86
                deltas.add(delta)
                cases += 1
        print(
            "REFERENCE_PASS,"
            f"t={T},M={M_SCALE},cases={cases},"
            f"reachable_deltas={len(deltas)},delta_min={min(deltas)},delta_max={max(deltas)}"
        )


if __name__ == "__main__":
    main()
