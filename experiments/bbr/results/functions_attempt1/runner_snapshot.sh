#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/results/functions_$(date -u +%Y%m%dT%H%M%SZ)"}
CERTS=${2:-"$ROOT/evidence/certificates_attempt1"}
INPUTS=${3:-"$ROOT/../../DCC_submission_polish_v4/experiments_functions/inputs"}
if [[ -e "$OUT" ]]; then echo 'Refusing existing run directory' >&2; exit 2; fi
mkdir -p "$OUT"
export PATH="$HOME/.cargo/bin:$PATH"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
{ uname -a; lscpu; rustc +1.96.0 --version; env | grep -E '^(RAYON|OMP|OPENBLAS)'; } > "$OUT/environment.txt"
cp "$ROOT/source/HLUT-rs/src/bin/matched_functions.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/decomposition.rs" "$OUT/decomposition_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/files.rs" "$OUT/files_snapshot.rs"
cp "$ROOT/source/HLUT-rs/Cargo.lock" "$OUT/Cargo.lock"
cp "$ROOT/parameters/optimizer_cjp_odd-128.csv" "$OUT/parameters.csv"
cp "$ROOT/scripts/run_functions.sh" "$OUT/runner_snapshot.sh"
cp "$INPUTS/manifest.json" "$OUT/input_manifest.json"
cp "$INPUTS/../scripts/task_definitions.py" "$OUT/task_definitions.py"
sha256sum "$ROOT/.build/release/matched_functions" > "$OUT/binary_sha256.txt"
TASKS=(lower_median3_6 mode3_6 set_interval4_6 set_threshold4_6 hamming_interval10 max3_6 range3_6 iqr3_6 mad3_6 distinct3_6)
for TASK in "${TASKS[@]}"; do
    CASE="$OUT/$TASK"
    mkdir "$CASE"
    cp "$CERTS/$TASK.json" "$CASE/certificate.json"
    cp "$INPUTS/$TASK.csv" "$CASE/input.csv"
    COMMAND=(taskset -c 0-7 "$ROOT/.build/release/matched_functions" "$CASE/certificate.json" "$CASE/input.csv" "$CASE/raw.jsonl")
    printf '%q ' "${COMMAND[@]}" > "$CASE/command.txt"
    printf '\n' >> "$CASE/command.txt"
    set +e
    /usr/bin/time -v -o "$CASE/resources.txt" "${COMMAND[@]}" > "$CASE/stdout.log" 2> "$CASE/stderr.log"
    RESULT=$?
    set -e
    printf '%s\n' "$RESULT" > "$CASE/exit_code.txt"
    printf '%s exit=%s\n' "$TASK" "$RESULT"
    if [[ "$RESULT" != 0 ]]; then
        printf 'FAILED task=%s; all completed records retained\n' "$TASK" > "$OUT/STATUS.txt"
        tail -n 12 "$CASE/stderr.log"
        exit "$RESULT"
    fi
done
printf 'COMPLETED ten tasks; 35 records per task\n' > "$OUT/STATUS.txt"
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
printf 'OUTPUT_DIR=%s\n' "$OUT"
