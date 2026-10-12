#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/toolchain/go/bin/go" ]]; then
  export GOROOT="$ROOT/toolchain/go"
  export PATH="$GOROOT/bin:$PATH"
fi
export GOPATH="$ROOT/toolchain/gopath"
export GOCACHE="$ROOT/build/gocache"
export GOMAXPROCS=2
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
LABEL="${1:-build_$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="$ROOT/results/$LABEL"
if [[ -e "$OUT" ]]; then echo "Refusing existing run $OUT"; exit 2; fi
mkdir -p "$OUT" "$ROOT/build"
cd "$ROOT/source/META-FBS"
if [[ -d .git ]]; then git rev-parse HEAD > "$OUT/upstream_commit.txt";
else cat "$ROOT/provenance/upstream_commit.txt" > "$OUT/upstream_commit.txt"; fi
go version > "$OUT/environment.txt"
uname -a >> "$OUT/environment.txt"
go build -p=2 -o "$ROOT/build/dccmeta" ./cmd/dccmeta > "$OUT/build.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/exit_code.txt"
cp go.mod go.sum "$OUT/"
echo "Build exit: $status"
tail -20 "$OUT/build.log"
exit "$status"
