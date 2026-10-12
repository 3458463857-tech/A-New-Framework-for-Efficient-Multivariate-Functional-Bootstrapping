#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory encrypted_checked "${1:-}" || exit $?
export RAYON_NUM_THREADS=8
export CARGO_TARGET_DIR="$ROOT/build/target"
cd "$ROOT/code/Section4_Code/tfhe_rs"
printf 'cargo build --release --locked --offline --bin bench_checked\n' > "$OUT/commands.txt"
cargo build --release --locked --offline --bin bench_checked > "$OUT/build.log" 2>&1
printf 'RAYON_NUM_THREADS=8 bench_checked representations/table11_representations.csv 30\n' >> "$OUT/commands.txt"
"$CARGO_TARGET_DIR/release/bench_checked" "$ROOT/results/revision_2026-10-10/representations/table11_representations.csv" 30 > "$OUT/checked.log" 2>&1
printf 'SUCCESS\n' > "$OUT/status.txt"
