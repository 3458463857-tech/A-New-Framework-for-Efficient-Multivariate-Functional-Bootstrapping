#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/results/bbr_cache_check"
if [[ -e "$OUT" ]]; then echo 'Refusing existing cache-check record' >&2; exit 2; fi
mkdir -p "$OUT"
SOURCE="$ROOT/../../DCC_revision_2026-10-10_v1/evidence/artifact-HLUT-TCHES-main/bench/HLUT-rs"
export CARGO_TARGET_DIR="$ROOT/build/bbr"
printf 'Read-only dependency resolution only; no benchmark executed.\ncargo +1.96.0 metadata --offline --locked --format-version 1 --manifest-path "$SOURCE/Cargo.toml"\n' > "$OUT/command.txt"
cp "$SOURCE/Cargo.toml" "$OUT/Cargo.toml"
cp "$SOURCE/Cargo.lock" "$OUT/Cargo.lock"
cargo +1.96.0 metadata --offline --locked --format-version 1 --manifest-path "$SOURCE/Cargo.toml" > "$OUT/stdout.txt" 2> "$OUT/stderr.txt"
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
exit "$status"
