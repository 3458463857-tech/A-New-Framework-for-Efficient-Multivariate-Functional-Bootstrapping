#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${1:-protocol_$(date -u +%Y%m%dT%H%M%SZ)}"
status=0
for size in 16 32 64; do
 bash "$ROOT/scripts/run_one.sh" dcc "$size" none "${PREFIX}_dcc_div${size}" || status=1
 bash "$ROOT/scripts/run_one.sh" native "$size" none "${PREFIX}_native_div${size}" || status=1
done
exit "$status"
