#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OLD="$ROOT/../../DCC_revision_v3/experiments_meta"
if [[ -x "$OLD/toolchain/go/bin/go" ]]; then
  export GOROOT="$OLD/toolchain/go"
  export PATH="$GOROOT/bin:$PATH"
fi
if [[ -d "$OLD/toolchain/gopath" ]]; then export GOPATH="$OLD/toolchain/gopath"; fi
export GOCACHE="$ROOT/build/gocache"
export GOPROXY=off
export GOMAXPROCS=8
ATTEMPT="${1:-build_attempt1}"
[[ "$ATTEMPT" =~ ^[A-Za-z0-9_-]+$ ]]
OUT="$ROOT/results/$ATTEMPT"
test ! -e "$OUT"
mkdir -p "$OUT" "$ROOT/build"
cp "$ROOT/source/META-FBS/cmd/dccextended/main.go" "$OUT/adapter_snapshot.go"
cd "$ROOT/source/META-FBS"
go version > "$OUT/environment.txt"
set +e
go build -p=8 -o "$ROOT/build/dccextended" ./cmd/dccextended > "$OUT/build.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$OUT/exit_code.txt"
tail -20 "$OUT/build.log"
exit "$status"
