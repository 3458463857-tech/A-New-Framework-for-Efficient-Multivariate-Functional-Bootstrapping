#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/results/build_rand_0_9_2"
if [[ -e "$OUT" ]]; then echo 'refusing to overwrite build attempt' >&2; exit 2; fi
mkdir -p "$OUT"
export CARGO_TARGET_DIR="$ROOT/build/refined"
export CARGO_NET_RETRY=0
export CARGO_HTTP_TIMEOUT=15
cd "$ROOT/source/refined-tfhe-lhe"
printf 'rand pinned to =0.9.2\ncargo bench --bench bench_lut_eval --no-run\n' > "$OUT/command.txt"
cargo bench --bench bench_lut_eval --no-run > "$OUT/build.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
exit "$status"
