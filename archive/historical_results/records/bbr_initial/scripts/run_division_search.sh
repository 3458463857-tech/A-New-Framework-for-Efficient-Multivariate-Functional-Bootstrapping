#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/results/division_search_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ -e "$OUT" ]] && [[ -n "$(ls -A "$OUT")" ]]; then echo 'Refusing nonempty output directory' >&2; exit 2; fi
mkdir -p "$OUT"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
/usr/bin/time -v -o "$OUT/resources.txt" timeout 300s taskset -c 0-7 "$ROOT/.venv/bin/python" "$ROOT/scripts/generate_division.py" > "$OUT/stdout.log" 2> "$OUT/stderr.log"
