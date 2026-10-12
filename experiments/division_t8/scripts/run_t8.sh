#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(cd "$ROOT/../.." && pwd)"
OUT="$ROOT/results/protocol1_attempt1"
test ! -e "$OUT"
mkdir -p "$OUT" "$ROOT/build"
export PATH="$HOME/.cargo/bin:$PATH"
export RAYON_NUM_THREADS=8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 GOMAXPROCS=8
export CARGO_NET_OFFLINE=true
export GOROOT="$WORK/DCC_revision_v3/experiments_meta/toolchain/go"
export GOPATH="$WORK/DCC_revision_v3/experiments_meta/toolchain/gopath"
export PATH="$GOROOT/bin:$PATH"
export GOCACHE="$ROOT/build/gocache" GOPROXY=off
date -u +%FT%TZ > "$OUT/started.txt"
uname -a > "$OUT/environment.txt"
lscpu >> "$OUT/environment.txt"
rustc --version >> "$OUT/environment.txt"
go version >> "$OUT/environment.txt"
cp "$ROOT/inputs/division_t8.csv" "$OUT/input_snapshot.csv"
sha256sum "$OUT/input_snapshot.csv" > "$OUT/input_sha256.txt"
# Copy build caches to a new directory; earlier source and build files stay untouched.
cp -a "$WORK/DCC_targeted_revision_v2/final_experiments/build/target" "$ROOT/build/target"
cp -a "$WORK/DCC_targeted_revision_v2/baseline_experiments/build/refined" "$ROOT/build/refined"
export CARGO_TARGET_DIR="$ROOT/build/target"
cd "$ROOT/source/section3"
cargo build --release --locked --offline --bin algorithm1_t8_audited --bin baseline_div_t8 > "$OUT/build_section3.log" 2>&1
echo 'BUILD section3 PASS'
export CARGO_TARGET_DIR="$ROOT/build/refined"
cd "$ROOT/source/refined-tfhe-lhe"
cargo bench --no-run --locked --offline --bench bench_targeted_div8 > "$OUT/build_refined.log" 2>&1
echo 'BUILD refined PASS'
cd "$ROOT/source/META-FBS"
go build -p=8 -o "$ROOT/build/dcct8" ./cmd/dcct8 > "$OUT/build_meta.log" 2>&1
echo 'BUILD meta PASS'
run_one(){
 local method="$1" source="$2"; shift 2
 local dir="$OUT/$method"
 mkdir -p "$dir"
 cp "$source" "$dir/source_snapshot.${source##*.}"
 sha256sum "$source" > "$dir/source_sha256.txt"
 printf '%q ' "$@" > "$dir/command.txt"; printf '\n' >> "$dir/command.txt"
 date -u +%FT%TZ > "$dir/started.txt"
 set +e
 taskset -c 0-7 "$@" > "$dir/run.log" 2>&1
 local status=$?
 set -e
 printf '%s\n' "$status" > "$dir/exit_code.txt"
 date -u +%FT%TZ > "$dir/finished.txt"
 tail -2 "$dir/run.log"
 if [[ "$status" != 0 ]]; then return "$status"; fi
}
export DCC_INPUT_MANIFEST="$ROOT/inputs/division_t8.csv"
run_one ours "$ROOT/source/section3/src/bin/algorithm1_t8_audited.rs" "$ROOT/build/target/release/algorithm1_t8_audited"
run_one native "$ROOT/source/section3/src/bin/baseline_div_t8.rs" "$ROOT/build/target/release/baseline_div_t8" 8 "$DCC_INPUT_MANIFEST"
refined_bin=$(find "$ROOT/build/refined/release/deps" -maxdepth 1 -type f -name 'bench_targeted_div8-*' -executable | head -1)
test -n "$refined_bin"
run_one refined "$ROOT/source/refined-tfhe-lhe/benches/bench_targeted_div8.rs" "$refined_bin" "$DCC_INPUT_MANIFEST"
run_one meta "$ROOT/source/META-FBS/cmd/dcct8/main.go" "$ROOT/build/dcct8" division_t8 "$DCC_INPUT_MANIFEST"
date -u +%FT%TZ > "$OUT/finished.txt"
echo 'COMPLETE four methods, each 5 warmups plus 30 measured trials'
