#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/build" "$ROOT/results/build"
export CARGO_TARGET_DIR="$ROOT/build/target"
export CARGO_NET_OFFLINE=true
export RAYON_NUM_THREADS=8
export CARGO_BUILD_JOBS=8
# Reuse a copy of the old dependency cache. Never modify the prior experiment.
OLD="$ROOT/../../DCC_targeted_revision_v2/baseline_experiments/build/refined"
if [[ ! -e "$CARGO_TARGET_DIR" && -d "$OLD" ]]; then
  cp -a "$OLD" "$CARGO_TARGET_DIR"
fi
cd "$ROOT/source/refined-tfhe-lhe"
printf 'cargo bench --no-run --locked --offline --bench bench_extended_div\n' > "$ROOT/results/build/command.txt"
set +e
cargo bench --no-run --locked --offline --bench bench_extended_div > "$ROOT/results/build/build.log" 2>&1
status=$?
printf '%s\n' "$status" > "$ROOT/results/build/exit_code.txt"
tail -20 "$ROOT/results/build/build.log"
exit "$status"
