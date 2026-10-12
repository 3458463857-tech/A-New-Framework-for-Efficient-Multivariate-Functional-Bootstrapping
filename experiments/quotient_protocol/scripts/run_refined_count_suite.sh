#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${1:-protocol_$(date -u +%Y%m%dT%H%M%SZ)}"
status=0
bash "$ROOT/scripts/run_one.sh" refined_div 16 none "${PREFIX}_refined_div16" || status=1
for width in 12 16; do
 for predicate in threshold interval; do
  bash "$ROOT/scripts/run_one.sh" count "$width" "$predicate" "${PREFIX}_dcc_n${width}_${predicate}" || status=1
  bash "$ROOT/scripts/run_one.sh" refined_count "$width" "$predicate" "${PREFIX}_refined_n${width}_${predicate}" || status=1
 done
done
exit "$status"
