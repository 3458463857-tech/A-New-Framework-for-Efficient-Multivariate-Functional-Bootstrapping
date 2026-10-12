from __future__ import annotations

import json
from pathlib import Path


def load_estimate(estimate_path: Path) -> int:
    with estimate_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    avg = data["mean"]["point_estimate"]
    return round(avg / 10e5)


def collect_results(base_dir: Path) -> dict[str, dict[int, int]]:
    results: dict[str, dict[int, int]] = {}

    for n_blocks in [1, 2, 4]:
        block_key = f"{n_blocks} blocks"
        results[block_key] = {}

        for precision_lut in range(4, 16):
            if precision_lut % n_blocks != 0:
                continue

            estimate_path = (
                base_dir
                / f"WOP-PBS with n_blocks = {n_blocks} and precision_lut = {precision_lut}"
                / "new"
                / "estimates.json"
            )

            results[block_key][precision_lut] = load_estimate(estimate_path)

    return results


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    woppbs_dir = script_dir.parent / "../../../" / "bench" / "bench_woppbs"
    output_dir = script_dir.parent / "../../../" / "data/regenerated"
    base_dir = woppbs_dir / "target" / "criterion"
    output_path = output_dir / "timings_wop-pbs.json"

    output_dir.mkdir(parents=True, exist_ok=True)

    results = collect_results(base_dir)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
