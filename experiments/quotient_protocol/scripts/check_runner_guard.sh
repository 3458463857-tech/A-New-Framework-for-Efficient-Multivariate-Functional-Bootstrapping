#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/results/runner_guard_check"
if [[ -e "$OUT" ]]; then echo 'Refusing existing validation record' >&2; exit 2; fi
mkdir -p "$OUT"
LOG="$ROOT/results/protocol1_dcc_n12_threshold/run.log"
sha256sum "$LOG" > "$OUT/before.sha256"
bash "$ROOT/scripts/run_one.sh" count 12 threshold protocol1_dcc_n12_threshold > "$OUT/guard.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
sha256sum "$LOG" > "$OUT/after.sha256"
[[ "$status" -eq 2 ]] && cmp "$OUT/before.sha256" "$OUT/after.sha256"
