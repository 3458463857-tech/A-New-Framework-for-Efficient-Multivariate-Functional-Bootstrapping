#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/results/counts_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ -e "$OUT" ]] && [[ -n "$(ls -A "$OUT")" ]]; then echo 'Refusing nonempty output directory' >&2; exit 2; fi
mkdir -p "$OUT"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
export PATH="$HOME/.cargo/bin:$PATH"
{ uname -a; lscpu; rustc +1.96.0 --version; taskset -cp $$; env | grep -E '^(RAYON|OMP|OPENBLAS)'; } > "$OUT/environment.txt"
cp "$ROOT/source/author/bench/HLUT-rs/src/bin/matched_tasks.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/source/author/bench/HLUT-rs/src/decomposition.rs" "$OUT/decomposition_snapshot.rs"
cp "$ROOT/source/author/bench/HLUT-rs/src/files.rs" "$OUT/files_snapshot.rs"
cp "$ROOT/source/author/bench/HLUT-rs/Cargo.lock" "$OUT/Cargo.lock"
for n in 12 16; do
  for task in count-threshold count-interval; do
    name="${task}_n${n}"
    printf '%s\n' "taskset -c 0-7 $ROOT/.build/release/matched_tasks $task $ROOT/inputs/count_n$n.csv $OUT/$name.jsonl" > "$OUT/$name.command.txt"
    /usr/bin/time -v -o "$OUT/$name.resources.txt" taskset -c 0-7 "$ROOT/.build/release/matched_tasks" "$task" "$ROOT/inputs/count_n$n.csv" "$OUT/$name.jsonl" > "$OUT/$name.stdout.log" 2> "$OUT/$name.stderr.log"
  done
done
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"
