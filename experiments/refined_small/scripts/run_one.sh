#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK="${1:?task required}"
INPUT="$(realpath "${2:?shared manifest required}")"
[[ "$TASK" =~ ^[a-zA-Z0-9_]+$ ]] || exit 2
OUT="$ROOT/results/protocol1_$TASK"
[[ ! -e "$OUT" ]] || { echo 'Refusing existing output'; exit 2; }
BIN=$(cat "$ROOT/results/current_executable.txt")
[[ -x "$BIN" && -f "$INPUT" ]] || { echo 'Missing executable or shared input'; exit 2; }
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 RUST_BACKTRACE=1
mkdir -p "$OUT"
SRC="$ROOT/source/refined-tfhe-lhe"
cp "$SRC/benches/bench_functions.rs" "$OUT/source_snapshot.rs"
cp "$SRC/Cargo.toml" "$SRC/Cargo.lock" "$OUT/"
cp "$INPUT" "$OUT/input_manifest.csv"
sha256sum "$OUT/source_snapshot.rs" "$OUT/Cargo.toml" "$OUT/Cargo.lock" "$OUT/input_manifest.csv" "$BIN" > "$OUT/hashes.txt"
{
 date -u --iso-8601=seconds
 uname -a
 lscpu
 rustc --version --verbose
 cargo --version
 printf 'RAYON_NUM_THREADS=8\nOMP_NUM_THREADS=8\nOPENBLAS_NUM_THREADS=8\nCPU affinity=0-7\nDefault monothread feature retained. Heavy tasks sequential.\n'
} > "$OUT/environment.txt" 2>&1
printf '%q ' taskset -c 0-7 "$BIN" "$TASK" "$INPUT" > "$OUT/command.txt"
printf '\n' >> "$OUT/command.txt"
/usr/bin/time -v -o "$OUT/process_resources.txt" taskset -c 0-7 "$BIN" "$TASK" "$INPUT" > "$OUT/run.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -4 "$OUT/run.log"
exit "$status"
