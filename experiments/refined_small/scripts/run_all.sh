#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUTS="${1:?canonical small-domain input directory required}"
for TASK in lower_median3_3 mode3_4 max3_3 range3_3 iqr3_4 mad3_3 distinct3_3; do
  printf 'Starting %s\n' "$TASK"
  bash "$ROOT/scripts/run_one.sh" "$TASK" "$INPUTS/$TASK.csv"
done
