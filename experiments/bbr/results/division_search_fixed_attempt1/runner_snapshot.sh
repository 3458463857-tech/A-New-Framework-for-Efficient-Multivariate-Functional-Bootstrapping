#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/results/division_search_fixed_$(date -u +%Y%m%dT%H%M%SZ)"}
# BBR_PYTHON may name a fresh virtualenv installed from source/decomposer.
PYTHON=${BBR_PYTHON:-"$ROOT/../../DCC_revision_v3/experiments_bbr/.venv/bin/python"}
if [[ -e "$OUT" ]]; then echo 'Refusing existing search record directory' >&2; exit 2; fi
mkdir -p "$OUT"
export PYTHONDONTWRITEBYTECODE=1 NUMBA_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 OMP_NUM_THREADS=8
{ uname -a; lscpu; "$PYTHON" --version; "$PYTHON" -m pip freeze; } > "$OUT/environment.txt"
cp "$ROOT/scripts/search_division_fixed.py" "$OUT/search_snapshot.py"
cp "$ROOT/scripts/run_division_search_fixed.sh" "$OUT/runner_snapshot.sh"
cp "$ROOT/parameters/optimizer_cjp_odd-128.csv" "$OUT/parameters.csv"
COMMAND=(timeout --signal=TERM --kill-after=5s 120s taskset -c 0-7 "$PYTHON" -u "$ROOT/scripts/search_division_fixed.py" --output-dir "$OUT/search")
printf '%q ' "${COMMAND[@]}" > "$OUT/command.txt"; printf '\n' >> "$OUT/command.txt"
set +e
/usr/bin/time -v -o "$OUT/resources.txt" "${COMMAND[@]}" > "$OUT/stdout.log" 2> "$OUT/stderr.log"
RESULT=$?
set -e
printf '%s\n' "$RESULT" > "$OUT/exit_code.txt"
"$PYTHON" - "$OUT" <<'PY'
from pathlib import Path
import json,sys
p=Path(sys.argv[1]); trace=p/'search/rank_trace.jsonl'
rows=[json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
code=int((p/'exit_code.txt').read_text())
result=dict(exit_code=code, timeout_seconds=120, completed_candidates=len(rows),
    maximum_rank=max((r['rank'] for r in rows),default=None),
    accepted_candidates=sum(r['accepted'] for r in rows),
    verified_certificate=(p/'search/DIVISION_CERTIFICATE.json').exists(),
    status='success' if code==0 else ('bounded_timeout' if code==124 else 'error'),
    scope='lambda25,a11,n2,s16,p17,seed20261010; this is not an impossibility claim')
(p/'STATUS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
exit "$RESULT"
