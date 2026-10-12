#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK="${1:?task}"; SIZE="${2:?size}"; PRED="${3:-none}"; LABEL="${4:?unique_label}"; LIMIT="${5:-}"
if [[ ! "$LABEL" =~ ^[a-zA-Z0-9_-]+$ ]]; then exit 2; fi
OUT="$ROOT/results/$LABEL"
if [[ -e "$OUT" ]]; then echo "Refusing existing output $OUT"; exit 2; fi
mkdir -p "$OUT"
if [[ -x "$ROOT/toolchain/go/bin/go" ]]; then
  export GOROOT="$ROOT/toolchain/go"; export PATH="$GOROOT/bin:$PATH"
fi
export GOMAXPROCS=8
if [[ "$TASK" = div ]]; then INPUT="$ROOT/inputs/division_t$SIZE.csv"; else INPUT="$ROOT/inputs/count_n$SIZE.csv"; fi
cp "$ROOT/source/META-FBS/cmd/dccmeta/main.go" "$OUT/adapter_snapshot.go"
cp "$ROOT/source/META-FBS/go.mod" "$ROOT/source/META-FBS/go.sum" "$OUT/"
cp "$INPUT" "$OUT/input_manifest.csv"
sha256sum "$OUT/adapter_snapshot.go" "$OUT/go.mod" "$OUT/go.sum" "$OUT/input_manifest.csv" "$ROOT/build/dccmeta" > "$OUT/hashes.txt"
if [[ -d "$ROOT/source/META-FBS/.git" ]]; then
  git -C "$ROOT/source/META-FBS" rev-parse HEAD > "$OUT/upstream_commit.txt"
else cat "$ROOT/provenance/upstream_commit.txt" > "$OUT/upstream_commit.txt"; fi
{ date -u --iso-8601=seconds; uname -a; lscpu; go version; printf 'GOMAXPROCS=8\nCPU affinity0-7\n'; } > "$OUT/environment.txt" 2>&1
ARGS=("$TASK" "$SIZE" "$PRED" "$INPUT"); if [[ -n "$LIMIT" ]]; then ARGS+=("$LIMIT"); fi
printf '%q ' taskset -c 0-7 "$ROOT/build/dccmeta" "${ARGS[@]}" > "$OUT/command.txt"
/usr/bin/time -v -o "$OUT/process_resources.txt" taskset -c 0-7 "$ROOT/build/dccmeta" "${ARGS[@]}" > "$OUT/run.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -7 "$OUT/run.log"
echo "Run exit: $status"
exit "$status"
