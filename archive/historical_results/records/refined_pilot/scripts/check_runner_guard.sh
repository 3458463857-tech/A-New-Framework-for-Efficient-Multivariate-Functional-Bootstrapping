#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/results/runner_guard_check"
if [[ -e "$OUT" ]]; then echo 'Refusing existing validation record' >&2; exit 2; fi
mkdir -p "$OUT"
sha256sum "$ROOT/results/div4_attempt1/run.log" > "$OUT/before.sha256"
bash "$ROOT/scripts/run_targeted_div4.sh" div4_attempt1 > "$OUT/stdout.txt" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
sha256sum "$ROOT/results/div4_attempt1/run.log" > "$OUT/after.sha256"
[[ "$status" -eq 2 ]] && cmp "$OUT/before.sha256" "$OUT/after.sha256"
