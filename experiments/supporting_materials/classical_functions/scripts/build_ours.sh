#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CARGO_NET_OFFLINE=true
export CARGO_BUILD_JOBS=8
export RAYON_NUM_THREADS=8
export CARGO_TARGET_DIR="$ROOT/ours/build/target"
ATTEMPT="${1:?provide a unique attempt name}"
OUT="$ROOT/ours/results/$ATTEMPT"
test ! -e "$OUT"
mkdir -p "$OUT"
cp "$ROOT/ours/src/bin/functions_checked.rs" "$OUT/source_snapshot.rs"
sha256sum "$OUT/source_snapshot.rs" > "$OUT/source_sha256.txt"
# Reuse compiled dependencies by copying the cache. Previous sources/records stay unchanged.
OLD="$ROOT/../../DCC_targeted_revision_v2/final_experiments/build/target"
if [[ ! -e "$CARGO_TARGET_DIR" && -d "$OLD" ]]; then
  mkdir -p "$(dirname "$CARGO_TARGET_DIR")"
  cp -a "$OLD" "$CARGO_TARGET_DIR"
fi
cd "$ROOT/ours"
printf '%s\n' 'cargo build --release --locked --offline --bin functions_checked' > "$OUT/command.txt"
set +e
cargo build --release --locked --offline --bin functions_checked > "$OUT/build.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -30 "$OUT/build.log"
exit "$status"
