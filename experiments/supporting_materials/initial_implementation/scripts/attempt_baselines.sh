#!/usr/bin/env bash
# Bounded setup attempts; neither command is a measured baseline evaluation.
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/output_directory.sh"
new_output_directory baseline_attempts "${2:-}" || exit $?
export CARGO_HTTP_TIMEOUT=15
export CARGO_NET_RETRY=0
if [[ $# -ge 1 ]]; then
  printf 'cargo +1.96.0 build --release --locked --offline --manifest-path BBR_SOURCE/bench/HLUT-rs/Cargo.toml\n' > "$OUT/bbr_command.txt"
  CARGO_TARGET_DIR="$ROOT/build/bbr" cargo +1.96.0 build --release --locked --offline --manifest-path "$1/bench/HLUT-rs/Cargo.toml" > "$OUT/bbr_build.log" 2>&1
  printf '%s\n' "$?" > "$OUT/bbr_exit_code.txt"
fi
cd "$ROOT/third_party/refined-tfhe-lhe"
printf 'CARGO_HTTP_TIMEOUT=15 CARGO_NET_RETRY=0 timeout 180 cargo bench --bench bench_lut_eval --no-run\n' > "$OUT/refined_command.txt"
CARGO_TARGET_DIR="$ROOT/build/refined" timeout 180 cargo bench --bench bench_lut_eval --no-run > "$OUT/refined_online_build.log" 2>&1
printf '%s\n' "$?" > "$OUT/refined_exit_code.txt"
