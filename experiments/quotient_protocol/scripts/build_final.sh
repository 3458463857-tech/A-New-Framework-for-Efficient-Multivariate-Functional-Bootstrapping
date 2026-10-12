#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${1:-build_final_$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$LABEL" =~ ^[a-zA-Z0-9_-]+$ ]]; then echo 'Invalid build label' >&2; exit 2; fi
OUT="$ROOT/results/$LABEL"
if [[ -e "$OUT" ]]; then echo 'Refusing existing output' >&2; exit 2; fi
mkdir -p "$OUT" "$ROOT/build"
export RAYON_NUM_THREADS=8
export CARGO_NET_OFFLINE=true
# Copy the prior dependency cache, never mutate the v1 target directory.
if [[ ! -e "$ROOT/build/target" && -d "$ROOT/../../DCC_revision_2026-10-10_v1/05_Reproducibility/build/target" ]]; then
 cp -a "$ROOT/../../DCC_revision_2026-10-10_v1/05_Reproducibility/build/target" "$ROOT/build/target"
fi
export CARGO_TARGET_DIR="$ROOT/build/target"
cd "$ROOT/source/section3"
printf 'cargo build --release --locked --offline --bin algorithm1_t16_audited --bin algorithm1_audited --bin baseline_div_final --bin count_checked_final\n' > "$OUT/section3_command.txt"
cargo build --release --locked --offline --bin algorithm1_t16_audited --bin algorithm1_audited --bin baseline_div_final --bin count_checked_final > "$OUT/section3.log" 2>&1
status=$?;printf '%s\n' "$status" > "$OUT/section3_exit.txt"
if [[ "$status" -ne 0 ]]; then exit "$status"; fi
if [[ -d "$ROOT/../baseline_experiments/build/refined" ]]; then
 export CARGO_TARGET_DIR="$ROOT/../baseline_experiments/build/refined"
else
 export CARGO_TARGET_DIR="$ROOT/build/refined"
fi
cd "$ROOT/source/refined-tfhe-lhe"
printf 'cargo bench --no-run --locked --offline --bench bench_targeted_div4 --bench bench_count_boolean\n' > "$OUT/refined_command.txt"
cargo bench --no-run --locked --offline --bench bench_targeted_div4 --bench bench_count_boolean > "$OUT/refined.log" 2>&1
status=$?;printf '%s\n' "$status" > "$OUT/refined_exit.txt"
exit "$status"
