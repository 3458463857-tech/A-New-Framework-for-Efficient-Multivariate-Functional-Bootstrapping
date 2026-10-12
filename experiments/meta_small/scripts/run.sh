#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUTS="$ROOT/inputs"
ATTEMPT="${1:-protocol1_attempt1}"
[[ "$ATTEMPT" =~ ^[A-Za-z0-9_-]+$ ]]
OUT="$ROOT/results/$ATTEMPT"
test ! -e "$OUT"
mkdir -p "$OUT"
export GOMAXPROCS=8
date -u +%FT%TZ > "$OUT/started.txt"
cp "$ROOT/source/META-FBS/cmd/dccsmall/main.go" "$OUT/adapter_snapshot.go"
cp "$ROOT/source/META-FBS/go.mod" "$ROOT/source/META-FBS/go.sum" "$OUT/"
sha256sum "$ROOT/build/dccsmall" "$OUT/adapter_snapshot.go" "$OUT/go.mod" "$OUT/go.sum" > "$OUT/source_sha256.txt"
uname -a > "$OUT/environment.txt"
for task in lower_median3_3 mode3_4 max3_3 range3_3 iqr3_4 mad3_3 distinct3_3; do
  input="$INPUTS/$task.csv"
  mkdir -p "$OUT/$task"
  cp "$input" "$OUT/$task/input_snapshot.csv"
  sha256sum "$input" > "$OUT/$task/input_sha256.txt"
  printf '%q ' "$ROOT/build/dccsmall" "$task" "$input" > "$OUT/$task/command.txt"
  printf '\n' >> "$OUT/$task/command.txt"
  date -u +%FT%TZ > "$OUT/$task/started.txt"
  set +e
  "$ROOT/build/dccsmall" "$task" "$input" > "$OUT/$task/run.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" > "$OUT/$task/exit_code.txt"
  date -u +%FT%TZ > "$OUT/$task/finished.txt"
  tail -2 "$OUT/$task/run.log"
  if [[ "$status" -ne 0 ]]; then exit "$status"; fi
done
date -u +%FT%TZ > "$OUT/finished.txt"
