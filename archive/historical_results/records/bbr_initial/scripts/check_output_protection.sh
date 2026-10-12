#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/results/runner_output_protection.log"
if [[ -e "$OUT" ]]; then echo 'refusing existing validation log' >&2; exit 2; fi
for runner in run_counts.sh run_division_search.sh build_environment.sh; do
  set +e
  bash "$ROOT/scripts/$runner" "$ROOT/results/counts_protocol1" >> "$OUT" 2>&1
  code=$?
  set -e
  printf '%s exit=%s expected=2\n' "$runner" "$code" >> "$OUT"
  test "$code" -eq 2
done
