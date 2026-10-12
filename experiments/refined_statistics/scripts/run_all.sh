#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUTS="$ROOT/../experiments_functions/inputs"
for TASK in lower_median3_6 mode3_6 set_interval4_6 set_threshold4_6 hamming_interval10 max3_6 range3_6 iqr3_6 mad3_6 distinct3_6; do
  printf 'Starting %s\n' "$TASK"
  bash "$ROOT/scripts/run_one.sh" "$TASK" "$INPUTS/$TASK.csv"
done
