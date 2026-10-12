#!/usr/bin/env bash
# All compilation precedes serial timings; no concurrent benchmark is launched.
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory encrypted_final "${1:-}" || exit $?
export RAYON_NUM_THREADS=8
export CARGO_TARGET_DIR="$ROOT/build/target"
{
 date -u --iso-8601=seconds
 uname -a
 lscpu
 rustc --version --verbose
 cargo --version
 printf 'RAYON_NUM_THREADS=8\nSequence=compile_all_then_run_serially\n'
} > "$OUT/environment.txt" 2>&1
cd "$ROOT/code/Section3_Code"
cargo build --release --locked --offline --bins > "$OUT/build_baseline.log" 2>&1
cd "$ROOT/code/Section4_Code/tfhe_rs"
cargo build --release --locked --offline --bin bench_checked > "$OUT/build_checked.log" 2>&1
run(){
 local name="$1"; shift
 printf '%s\t' "$name" >> "$OUT/commands.tsv"
 printf '%q ' "$@" >> "$OUT/commands.tsv"
 printf '\n' >> "$OUT/commands.tsv"
 "$@" > "$OUT/$name.log" 2>&1
 printf '%s\t0\n' "$name" >> "$OUT/exit_codes.tsv"
 printf '%s PASS\n' "$name"
}
run checked "$CARGO_TARGET_DIR/release/bench_checked" "$ROOT/results/revision_2026-10-10/representations/table11_representations.csv" 30
run division16 "$CARGO_TARGET_DIR/release/section3-algorithm1-reproduction" --samples 30
run baseline16 "$CARGO_TARGET_DIR/release/baseline_div" 16
run division32 "$CARGO_TARGET_DIR/release/algorithm1_small_parameter" --t 32 --samples 30
run baseline32 "$CARGO_TARGET_DIR/release/baseline_div" 32
run division64 "$CARGO_TARGET_DIR/release/algorithm1_small_parameter" --t 64 --samples 30
run baseline64 "$CARGO_TARGET_DIR/release/baseline_div" 64
printf 'SUCCESS\n' > "$OUT/status.txt"
