#!/usr/bin/env bash
# Additional noise-budget-repaired circuit; original recorded implementation remains available.
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory division_checked "${1:-}" || exit $?
export RAYON_NUM_THREADS=8
export RUST_BACKTRACE=1
export CARGO_TARGET_DIR="$ROOT/build/target"
cd "$ROOT/code/Section3_Code"
printf 'cargo build --release --locked --offline --bin algorithm1_noise_checked\nRAYON_NUM_THREADS=8 algorithm1_noise_checked --t 64 --samples 30\n' > "$OUT/commands.txt"
{
 date -u --iso-8601=seconds
 uname -a
 rustc --version
 cargo --version
 printf 'RAYON_NUM_THREADS=8\n'
} > "$OUT/environment.txt" 2>&1
cargo build --release --locked --offline --bin algorithm1_noise_checked > "$OUT/build.log" 2>&1
status=$?
printf 'build\t%s\n' "$status" > "$OUT/exit_codes.tsv"
if [[ $status -ne 0 ]]; then exit "$status"; fi
"$CARGO_TARGET_DIR/release/algorithm1_noise_checked" --t 64 --samples 30 > "$OUT/division_checked64.log" 2>&1
status=$?
printf 'run\t%s\n' "$status" >> "$OUT/exit_codes.tsv"
exit "$status"
