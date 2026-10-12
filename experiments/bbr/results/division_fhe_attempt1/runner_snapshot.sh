#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SEARCH=${1:?Provide the successful fixed-shape search record directory}
OUT=${2:-"$ROOT/results/division_fhe_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ -e "$OUT" ]]; then echo 'Refusing existing FHE record directory' >&2; exit 2; fi
if [[ ! -f "$SEARCH/search/DIVISION_CERTIFICATE.json" ]]; then echo 'A verified search certificate is required' >&2; exit 2; fi
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$ROOT/.build"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
NAME="division_t16_lambda25_a11_$(basename "$OUT")"
if [[ -e "$ROOT/decompositions/$NAME" ]]; then echo 'Refusing existing decomposition directory' >&2; exit 2; fi
mkdir -p "$ROOT/decompositions/$NAME"
cp "$SEARCH/search/decomposition/"* "$ROOT/decompositions/$NAME/"
cp "$SEARCH/search/DIVISION_CERTIFICATE.json" "$OUT/certificate.json"
cp "$ROOT/shared_protocol/inputs/division_t16.csv" "$OUT/input.csv"
cp "$ROOT/source/HLUT-rs/src/bin/matched_division.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/decomposition.rs" "$OUT/decomposition_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/files.rs" "$OUT/files_snapshot.rs"
cp "$ROOT/source/HLUT-rs/Cargo.lock" "$OUT/Cargo.lock"
cp "$ROOT/parameters/optimizer_cjp_odd-128.csv" "$OUT/parameters.csv"
cp "$ROOT/scripts/run_division_fhe.sh" "$OUT/runner_snapshot.sh"
{ uname -a; lscpu; rustc +1.96.0 --version; env | grep -E '^(RAYON|OMP|OPENBLAS)'; } > "$OUT/environment.txt"
cd "$ROOT/source/HLUT-rs"
printf '%s\n' 'cargo +1.96.0 build --release --locked --offline --bin matched_division' > "$OUT/build_command.txt"
set +e
/usr/bin/time -v -o "$OUT/build_resources.txt" cargo +1.96.0 build --release --locked --offline --bin matched_division > "$OUT/build_stdout.log" 2> "$OUT/build_stderr.log"
RESULT=$?
set -e
printf '%s\n' "$RESULT" > "$OUT/build_exit_code.txt"
if [[ "$RESULT" == 0 ]]; then
    sha256sum "$ROOT/.build/release/matched_division" > "$OUT/binary_sha256.txt"
    COMMAND=(taskset -c 0-7 "$ROOT/.build/release/matched_division" "$NAME" "$OUT/input.csv" "$OUT/raw.jsonl")
    printf '%q ' "${COMMAND[@]}" > "$OUT/command.txt"; printf '\n' >> "$OUT/command.txt"
    set +e
    /usr/bin/time -v -o "$OUT/resources.txt" "${COMMAND[@]}" > "$OUT/stdout.log" 2> "$OUT/stderr.log"
    RESULT=$?
    set -e
    printf '%s\n' "$RESULT" > "$OUT/exit_code.txt"
fi
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
printf 'OUTPUT_DIR=%s exit=%s\n' "$OUT" "$RESULT"
exit "$RESULT"
