#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${1:-div4_$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$LABEL" =~ ^[a-zA-Z0-9_-]+$ ]]; then echo 'Invalid output label' >&2; exit 2; fi
OUT="$ROOT/results/$LABEL"
if [[ -e "$OUT" ]]; then echo "Refusing existing output: $OUT" >&2; exit 2; fi
mkdir -p "$OUT"
export CARGO_TARGET_DIR="$ROOT/build/refined"
export RAYON_NUM_THREADS=8
export CARGO_NET_OFFLINE=true
export RUST_BACKTRACE=1
cd "$ROOT/source/refined-tfhe-lhe"
cp benches/bench_targeted_div4.rs "$OUT/source_snapshot.rs"
cp Cargo.toml "$OUT/Cargo.toml"
cp Cargo.lock "$OUT/Cargo.lock"
{
  date -u --iso-8601=seconds
  uname -a
  lscpu
  rustc --version --verbose
  cargo --version
  printf 'RAYON_NUM_THREADS=%s\nCARGO_NET_OFFLINE=%s\nFeatures=default (author monothread)\n' "$RAYON_NUM_THREADS" "$CARGO_NET_OFFLINE"
} > "$OUT/environment.txt" 2>&1
printf 'cargo bench --locked --offline --bench bench_targeted_div4\n' > "$OUT/command.txt"
cargo bench --locked --offline --bench bench_targeted_div4 > "$OUT/run.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
exit "$status"
