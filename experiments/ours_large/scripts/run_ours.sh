#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RAYON_NUM_THREADS=8
export OMP_NUM_THREADS=8
BIN="$ROOT/ours/build/target/release/functions_checked"
ATTEMPT="${1:-protocol1_attempt1}"
[[ "$ATTEMPT" =~ ^[A-Za-z0-9_-]+$ ]]
OUT="$ROOT/ours/results/$ATTEMPT"
mkdir -p "$OUT"
test ! -e "$OUT/started.txt"
date -u +%FT%TZ > "$OUT/started.txt"
cp "$ROOT/ours/src/bin/functions_checked.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/ours/Cargo.toml" "$OUT/Cargo.toml"
cp "$ROOT/ours/Cargo.lock" "$OUT/Cargo.lock"
sha256sum "$BIN" "$OUT/source_snapshot.rs" "$OUT/Cargo.toml" "$OUT/Cargo.lock" > "$OUT/source_sha256.txt"
uname -a > "$OUT/environment.txt"
lscpu >> "$OUT/environment.txt"
"$BIN" --certify-all > "$OUT/plaintext_rust_certificate.csv"
tasks=(lower_median3_6 mode3_6 set_interval4_6 set_threshold4_6 hamming_interval10 max3_6 range3_6 iqr3_6 mad3_6 distinct3_6)
for task in "${tasks[@]}"; do
  parameter=m2c4
  if [[ "$task" == hamming_interval10 ]]; then parameter=m1c4; fi
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
