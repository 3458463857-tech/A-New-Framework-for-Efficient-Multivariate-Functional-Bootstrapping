#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=${1:?Provide 8 or 32}
OUT=${2:-"$ROOT/results/search_t${T}_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ "$T" == 8 ]]; then LIMIT=120; elif [[ "$T" == 32 ]]; then LIMIT=180; else exit 2; fi
if [[ -e "$OUT" ]]; then echo 'Refusing existing search record directory' >&2; exit 2; fi
PYTHON=${BBR_PYTHON:-"$ROOT/../../../DCC_revision_v3/experiments_bbr/.venv/bin/python"}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
export PYTHONDONTWRITEBYTECODE=1 NUMBA_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 OMP_NUM_THREADS=8
{ uname -a; lscpu; "$PYTHON" --version; "$PYTHON" -m pip freeze; } > "$OUT/environment.txt"
cp "$ROOT/scripts/search_division_domains.py" "$OUT/search_snapshot.py"
cp "$ROOT/scripts/run_search.sh" "$OUT/runner_snapshot.sh"
cp "$ROOT/parameters/optimizer_cjp_odd-128.csv" "$OUT/parameters.csv"
COMMAND=(timeout --signal=TERM --kill-after=5s "${LIMIT}s" taskset -c 0-7 "$PYTHON" -u "$ROOT/scripts/search_division_domains.py" --t "$T" --output-dir "$OUT/search")
printf '%q ' "${COMMAND[@]}" > "$OUT/command.txt"; printf '\n' >> "$OUT/command.txt"
set +e
/usr/bin/time -v -o "$OUT/resources.txt" "${COMMAND[@]}" > "$OUT/stdout.log" 2> "$OUT/stderr.log"
RESULT=$?
set -e
printf '%s\n' "$RESULT" > "$OUT/exit_code.txt"
"$PYTHON" - "$OUT" "$LIMIT" <<'PY'
from pathlib import Path
import json,sys
p=Path(sys.argv[1]); trace=p/'search/rank_trace.jsonl'
rows=[json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
code=int((p/'exit_code.txt').read_text())
result=dict(exit_code=code, timeout_seconds=int(sys.argv[2]),
    events=rows, verified_certificate=(p/'search/DIVISION_CERTIFICATE.json').exists(),
    status='success' if code==0 else ('bounded_timeout' if code==124 else 'error'),
    scope='One fixed-seed, fixed-shape bounded invocation; not an impossibility claim')
(p/'STATUS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
exit "$RESULT"
