#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
METHOD="${1:?method required}"; SIZE="${2:?size required}"; PRED="${3:-none}"
LABEL="${4:-${METHOD}_${SIZE}_${PRED}_$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$LABEL" =~ ^[a-zA-Z0-9_-]+$ ]]; then echo 'Invalid output label' >&2; exit 2; fi
OUT="$ROOT/results/$LABEL"
if [[ -e "$OUT" ]]; then echo "Refusing existing output: $OUT" >&2; exit 2; fi
export RAYON_NUM_THREADS=8
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export RUST_BACKTRACE=1
case "$METHOD" in
 dcc)
  if [[ "$SIZE" = 16 ]]; then NAME=algorithm1_t16_audited; ARGS=(); else NAME=algorithm1_audited; ARGS=(--t "$SIZE"); fi
  SRC="$ROOT/source/section3"; BIN="$ROOT/build/target/release/$NAME"; SOURCE="$SRC/src/bin/$NAME.rs"
  INPUT="$ROOT/inputs/division_t$SIZE.csv"; export DCC_INPUT_MANIFEST="$INPUT" ;;
 native)
  SRC="$ROOT/source/section3"; NAME=baseline_div_final; BIN="$ROOT/build/target/release/$NAME"; SOURCE="$SRC/src/bin/$NAME.rs"
  INPUT="$ROOT/inputs/division_t$SIZE.csv"; ARGS=("$SIZE" "$INPUT") ;;
 count)
  SRC="$ROOT/source/section3"; NAME=count_checked_final; BIN="$ROOT/build/target/release/$NAME"; SOURCE="$SRC/src/bin/$NAME.rs"
  INPUT="$ROOT/inputs/count_n$SIZE.csv"; ARGS=("$SIZE" "$PRED" "$INPUT") ;;
 refined_div|refined_count)
  SRC="$ROOT/source/refined-tfhe-lhe"
  if [[ "$METHOD" = refined_div ]]; then
   NAME=bench_targeted_div4; INPUT="$ROOT/inputs/division_t$SIZE.csv"; ARGS=("$INPUT")
  else
   NAME=bench_count_boolean; INPUT="$ROOT/inputs/count_n$SIZE.csv"; ARGS=("$SIZE" "$PRED" "$INPUT")
  fi
  SOURCE="$SRC/benches/$NAME.rs"
  BUILD_LOG=$(ls -t "$ROOT"/results/*/refined.log | head -1)
  BIN=$(sed -n "s/.*Executable benches\/$NAME.rs (\(.*\))/\1/p" "$BUILD_LOG" | tail -1) ;;
 *) echo 'Unknown method' >&2; exit 2 ;;
esac
if [[ ! -f "$INPUT" || ! -x "$BIN" ]]; then echo "Missing input or executable: $INPUT ; $BIN" >&2; exit 2; fi
mkdir -p "$OUT"
cp "$SOURCE" "$OUT/source_snapshot.rs"
cp "$SRC/Cargo.toml" "$OUT/Cargo.toml"
cp "$SRC/Cargo.lock" "$OUT/Cargo.lock"
cp "$INPUT" "$OUT/input_manifest.csv"
sha256sum "$OUT/source_snapshot.rs" "$OUT/Cargo.toml" "$OUT/Cargo.lock" "$OUT/input_manifest.csv" "$BIN" > "$OUT/hashes.txt"
{
 date -u --iso-8601=seconds
 uname -a
 lscpu
 rustc --version --verbose
 cargo --version
 printf 'RAYON_NUM_THREADS=8\nOMP_NUM_THREADS=8\nOPENBLAS_NUM_THREADS=8\nCPU affinity=0-7 (taskset; all implementation threads share 8 logical CPUs)\nHeavy benchmarks execute sequentially.\n'
} > "$OUT/environment.txt" 2>&1
printf '%q ' taskset -c 0-7 "$BIN" "${ARGS[@]}" > "$OUT/command.txt"
printf '\nDCC_INPUT_MANIFEST=%s\n' "${DCC_INPUT_MANIFEST:-unused}" >> "$OUT/command.txt"
printf 'method=%s\nsize=%s\npredicate=%s\n' "$METHOD" "$SIZE" "$PRED" > "$OUT/run_identity.txt"
/usr/bin/time -v -o "$OUT/process_resources.txt" taskset -c 0-7 "$BIN" "${ARGS[@]}" > "$OUT/run.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
printf 'Completed %s with exit %s\n' "$LABEL" "$status"
exit "$status"
