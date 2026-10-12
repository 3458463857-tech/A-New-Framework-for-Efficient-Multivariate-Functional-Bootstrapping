#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/results/build_small_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ -e "$OUT" ]]; then echo 'Refusing existing build record directory' >&2; exit 2; fi
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$ROOT/.build"
{ uname -a; lscpu; rustc +1.96.0 --version; } > "$OUT/environment.txt"
printf '%s\n' 'cargo +1.96.0 build --release --locked --offline --bin matched_small_functions' > "$OUT/command.txt"
cp "$ROOT/source/HLUT-rs/src/bin/matched_small_functions.rs" "$OUT/source_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/decomposition.rs" "$OUT/decomposition_snapshot.rs"
cp "$ROOT/source/HLUT-rs/src/files.rs" "$OUT/files_snapshot.rs"
cp "$ROOT/source/HLUT-rs/Cargo.lock" "$OUT/Cargo.lock"
cd "$ROOT/source/HLUT-rs"
set +e
/usr/bin/time -v -o "$OUT/resources.txt" cargo +1.96.0 build --release --locked --offline --bin matched_small_functions > "$OUT/stdout.log" 2> "$OUT/stderr.log"
RESULT=$?
set -e
printf '%s\n' "$RESULT" > "$OUT/exit_code.txt"
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
tail -n 8 "$OUT/stderr.log"
exit "$RESULT"
