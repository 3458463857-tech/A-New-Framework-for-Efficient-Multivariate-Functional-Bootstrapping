#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${1:?unique_suite_prefix}"
bash "$ROOT/scripts/run_meta.sh" div 16 none "${PREFIX}_div16"
for size in 12 16; do
  for predicate in threshold interval; do
    bash "$ROOT/scripts/run_meta.sh" count "$size" "$predicate" "${PREFIX}_count${size}_${predicate}"
  done
done
