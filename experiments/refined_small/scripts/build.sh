#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${1:-build_attempt1}"
[[ "$LABEL" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
OUT="$ROOT/results/$LABEL"
[[ ! -e "$OUT" ]] || { echo 'Refusing existing build record'; exit 2; }
mkdir -p "$ROOT/build" "$OUT"
export CARGO_TARGET_DIR="$ROOT/build/target" CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=8 RAYON_NUM_THREADS=8
OLD="$ROOT/../../DCC_submission_polish_v4/experiments_refined_functions/build/target"
if [[ ! -e "$CARGO_TARGET_DIR" && -d "$OLD" ]]; then cp -a "$OLD" "$CARGO_TARGET_DIR"; fi
cd "$ROOT/source/refined-tfhe-lhe"
cp benches/bench_functions.rs "$OUT/source_snapshot.rs"
printf 'cargo bench --no-run --locked --offline --bench bench_functions\n' > "$OUT/command.txt"
set +e
cargo bench --no-run --locked --offline --bench bench_functions > "$OUT/build.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -20 "$OUT/build.log"
if [[ "$status" == 0 ]]; then
 sed -n 's/.*Executable benches\/bench_functions.rs (\(.*\))/\1/p' "$OUT/build.log" | tail -1 > "$ROOT/results/current_executable.txt"
fi
exit "$status"
