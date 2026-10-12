#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
T="${1:?t required}"
[[ "$T" == 32 || "$T" == 64 ]] || exit 2
OUT="$ROOT/results/protocol1_refined_div$T"
[[ ! -e "$OUT" ]] || { echo 'Refusing existing output'; exit 2; }
BIN=$(sed -n 's/.*Executable benches\/bench_extended_div.rs (\(.*\))/\1/p' "$ROOT/results/build/build.log" | tail -1)
INPUT="$ROOT/inputs/division_t$T.csv"
SRC="$ROOT/source/refined-tfhe-lhe"
[[ -x "$BIN" ]] || { echo "No executable: $BIN"; exit 2; }
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 RUST_BACKTRACE=1
mkdir -p "$OUT"
cp "$SRC/benches/bench_extended_div.rs" "$OUT/source_snapshot.rs"
cp "$SRC/Cargo.toml" "$SRC/Cargo.lock" "$OUT/"
cp "$INPUT" "$OUT/input_manifest.csv"
sha256sum "$OUT/source_snapshot.rs" "$OUT/Cargo.toml" "$OUT/Cargo.lock" "$INPUT" "$BIN" > "$OUT/hashes.txt"
{
 date -u --iso-8601=seconds
 uname -a
 lscpu
 rustc --version --verbose
 cargo --version
 printf 'RAYON_NUM_THREADS=8\nOMP_NUM_THREADS=8\nOPENBLAS_NUM_THREADS=8\nCPU affinity=0-7\nAuthor default monothread feature retained. Heavy tasks run sequentially.\n'
} > "$OUT/environment.txt" 2>&1
printf '%q ' taskset -c 0-7 "$BIN" "$T" "$INPUT" > "$OUT/command.txt"
printf '\n' >> "$OUT/command.txt"
/usr/bin/time -v -o "$OUT/process_resources.txt" taskset -c 0-7 "$BIN" "$T" "$INPUT" > "$OUT/run.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -4 "$OUT/run.log"
exit "$status"
