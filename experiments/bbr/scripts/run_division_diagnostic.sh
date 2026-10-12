#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:?fresh absolute output directory required}
MODE=${2:-original}
if [[ -e "$OUT" ]]; then echo 'Refusing existing diagnostic directory' >&2; exit 2; fi
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$ROOT/.build"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
cp "$ROOT/source/HLUT-rs/src/bin/diagnose_division.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/decomposition.rs" "$OUT/decomposition_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/files.rs" "$OUT/files_snapshot.rs"
cp "$ROOT/source/HLUT-rs/Cargo.lock" "$OUT/Cargo.lock"
cp "$0" "$OUT/runner_snapshot.sh"
{ uname -a; rustc +1.96.0 --version; env | grep -E '^(RAYON|OMP|OPENBLAS)'; } > "$OUT/environment.txt"
cd "$ROOT/source/HLUT-rs"
printf '%s\n' 'cargo +1.96.0 build --release --locked --offline --bin diagnose_division' > "$OUT/build_command.txt"
set +e
/usr/bin/time -v -o "$OUT/build_resources.txt" cargo +1.96.0 build --release --locked --offline --bin diagnose_division > "$OUT/build_stdout.log" 2> "$OUT/build_stderr.log"
RESULT=$?; set -e; echo "$RESULT" > "$OUT/build_exit_code.txt"
if [[ "$RESULT" == 0 ]]; then
 sha256sum "$ROOT/.build/release/diagnose_division" > "$OUT/binary_sha256.txt"
 COMMAND=(taskset -c 0-7 "$ROOT/.build/release/diagnose_division" division_t16_lambda25_a11_division_fhe_attempt1 "$OUT/stages.jsonl" 0 15 "$MODE")
 printf '%q ' "${COMMAND[@]}" > "$OUT/command.txt"; printf '\n' >> "$OUT/command.txt"
 set +e
 /usr/bin/time -v -o "$OUT/resources.txt" "${COMMAND[@]}" > "$OUT/stdout.log" 2> "$OUT/stderr.log"
 RESULT=$?; set -e; echo "$RESULT" > "$OUT/exit_code.txt"
fi
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) > "$OUT/SHA256SUMS"
echo "OUTPUT_DIR=$OUT exit=$RESULT"
exit "$RESULT"
