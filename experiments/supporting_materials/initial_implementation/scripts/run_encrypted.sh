#!/usr/bin/env bash
# Run from any directory. The locked dependency build is offline by default.
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory encrypted_diagnostic "${1:-}" || exit $?
export RAYON_NUM_THREADS=8
export CARGO_TARGET_DIR="$ROOT/build/target"
{
  date -u --iso-8601=seconds
  uname -a
  cat /etc/os-release
  lscpu
  free -h
  rustc --version --verbose
  cargo --version
  printf 'RAYON_NUM_THREADS=%s\n' "$RAYON_NUM_THREADS"
  printf 'CARGO_TARGET_DIR=build/target\n'
} > "$OUT/environment.txt" 2>&1
run() {
  local name="$1"; shift
  printf '%s\t' "$name" >> "$OUT/commands.tsv"
  printf '%q ' "$@" >> "$OUT/commands.tsv"
  printf '\n' >> "$OUT/commands.tsv"
  "$@" > "$OUT/$name.log" 2>&1
  local status=$?
  printf '%s\t%s\n' "$name" "$status" >> "$OUT/exit_codes.tsv"
  printf '%s exit=%s\n' "$name" "$status"
  return "$status"
}
cd "$ROOT/code/Section4_Code/tfhe_rs"
if run build_section4 cargo build --release --locked --offline --bin bench_table11; then
  run section4 "$CARGO_TARGET_DIR/release/bench_table11" "$ROOT/results/revision_2026-10-10/representations/table11_representations.csv" 30
fi
cd "$ROOT/code/Section3_Code"
if run build_section3 cargo build --release --locked --offline; then
  run division16 "$CARGO_TARGET_DIR/release/section3-algorithm1-reproduction" --samples 30
  run division32 "$CARGO_TARGET_DIR/release/algorithm1_small_parameter" --t 32 --samples 30
  run division64 "$CARGO_TARGET_DIR/release/algorithm1_small_parameter" --t 64 --samples 30
fi
