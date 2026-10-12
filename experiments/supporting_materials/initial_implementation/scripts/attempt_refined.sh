#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory baseline_refined "${1:-}" || exit $?
cd "$ROOT/third_party/refined-tfhe-lhe"
printf 'cargo bench --offline --bench bench_lut_eval --no-run\n' > "$OUT/commands.txt"
CARGO_TARGET_DIR="$ROOT/build/refined" cargo bench --offline --bench bench_lut_eval --no-run > "$OUT/build.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
exit "$status"
