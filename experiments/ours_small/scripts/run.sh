#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ATTEMPT="${1:-protocol1_attempt1}"
[[ "$ATTEMPT" =~ ^[A-Za-z0-9_-]+$ ]]
OUT="$ROOT/ours/results/$ATTEMPT"
test ! -e "$OUT"
mkdir -p "$OUT"
export RAYON_NUM_THREADS=8
export OMP_NUM_THREADS=8
BIN="$ROOT/ours/build/target/release/functions_checked"
date -u +%FT%TZ > "$OUT/started.txt"
cp "$ROOT/ours/src/bin/functions_checked.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/ours/Cargo.toml" "$ROOT/ours/Cargo.lock" "$OUT/"
sha256sum "$BIN" "$OUT/source_snapshot.rs" "$OUT/Cargo.toml" "$OUT/Cargo.lock" > "$OUT/source_sha256.txt"
uname -a > "$OUT/environment.txt"
"$BIN" --certify-all > "$OUT/plaintext_rust_certificate.csv"
for task in hamming_interval10 set_interval4_6 set_threshold4_6 lower_median3_3 mode3_4 max3_3 range3_3 iqr3_4 mad3_3 distinct3_3; do
  parameter=m2c2
  if [[ "$task" == hamming_interval10 ]]; then parameter=m1c3; fi
  if [[ "$task" == mode3_4 || "$task" == iqr3_4 ]]; then parameter=m2c3; fi
  mkdir -p "$OUT/$task"
  cp "$ROOT/inputs/$task.csv" "$OUT/$task/input_snapshot.csv"
  sha256sum "$ROOT/inputs/$task.csv" > "$OUT/$task/input_sha256.txt"
  printf '%q ' "$BIN" --run --task "$task" --parameter "$parameter" --manifest "$ROOT/inputs/$task.csv" > "$OUT/$task/command.txt"
  printf '\n' >> "$OUT/$task/command.txt"
  date -u +%FT%TZ > "$OUT/$task/started.txt"
  set +e
  "$BIN" --run --task "$task" --parameter "$parameter" --manifest "$ROOT/inputs/$task.csv" > "$OUT/$task/run.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" > "$OUT/$task/exit_code.txt"
  date -u +%FT%TZ > "$OUT/$task/finished.txt"
  tail -2 "$OUT/$task/run.log"
  if [[ "$status" -ne 0 ]]; then exit "$status"; fi
done
date -u +%FT%TZ > "$OUT/finished.txt"
