#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPETITIONS="${1:-30}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT/experiment_records/run_$RUN_ID"

if ! [[ "$REPETITIONS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Usage: $0 [positive_repetition_count]" >&2
    exit 2
fi

for required_command in python3 rustc cargo sha256sum; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        echo "Missing required command: $required_command" >&2
        exit 2
    fi
done

mkdir -p "$RUN_DIR"

{
    echo "run_id=$RUN_ID"
    echo "utc_started=$(date -u --iso-8601=seconds)"
    echo "root=$ROOT"
    echo "repetitions=$REPETITIONS"
    echo "experiment=table11"
    echo "host_os=Microsoft Windows 11"
    echo "host_physical_memory_gib=24"
    uname -a
    cat /etc/os-release
    lscpu
    free -h
    python3 --version
    rustc --version
    cargo --version
} > "$RUN_DIR/environment.txt"

RUNNER_OS="$(. /etc/os-release; printf '%s' "$PRETTY_NAME")"
CPU_MODEL="$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1)"
{
    echo "run_id=$RUN_ID"
    echo "repetitions=$REPETITIONS"
    echo "experiment=table11"
    echo "host_os=Microsoft Windows 11"
    echo "host_physical_memory_gib=24"
    echo "runner_os=$RUNNER_OS"
    echo "kernel=$(uname -r)"
    echo "cpu_model=$CPU_MODEL"
    echo "physical_cores=20"
    echo "logical_cpus=$(nproc)"
    echo "wsl_memory_kib=$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
    echo "python_version=$(python3 --version 2>&1)"
    echo "rustc_version=$(rustc --version)"
    echo "cargo_version=$(cargo --version)"
    echo "tfhe_rs_version=0.8.7"
} > "$RUN_DIR/environment_kv.txt"

python3 "$ROOT/chapter4_compression/generate_table11_records.py" \
    --output-dir "$ROOT/chapter4_compression/records" \
    | tee "$RUN_DIR/table11_representation_generation.log"
cp "$ROOT/chapter4_compression/records/table11_representations.json" \
    "$RUN_DIR/table11_representations.json"
cp "$ROOT/chapter4_compression/records/table11_representations.csv" \
    "$RUN_DIR/table11_representations.csv"

python3 -m unittest discover -s "$ROOT/tests" -v \
    2>&1 | tee "$RUN_DIR/chapter4_reference_tests.log"

pushd "$ROOT/tfhe_rs" >/dev/null
RUSTFLAGS="-C target-cpu=native" cargo build --release --locked --bin bench_table11
RUSTFLAGS="-C target-cpu=native" cargo run --release --locked --bin bench_table11 -- \
    "$ROOT/chapter4_compression/records/table11_representations.csv" \
    "$REPETITIONS" | tee "$RUN_DIR/table11.log"
cargo tree --locked > "$RUN_DIR/cargo_tree.txt"
popd >/dev/null

sha256sum \
    "$ROOT/chapter4_compression/generate_table11_records.py" \
    "$ROOT/chapter4_compression/records/table11_representations.json" \
    "$ROOT/chapter4_compression/records/table11_representations.csv" \
    "$ROOT/tfhe_rs/src/bin/bench_table11.rs" \
    "$ROOT/tfhe_rs/Cargo.toml" \
    "$ROOT/tfhe_rs/Cargo.lock" \
    > "$RUN_DIR/artifact_hashes.sha256"

python3 "$ROOT/scripts/summarize_experiments.py" "$RUN_DIR"
cp "$RUN_DIR/experiment_values.tex" "$ROOT/section5/experiment_values.tex"
echo "utc_finished=$(date -u --iso-8601=seconds)" >> "$RUN_DIR/environment.txt"
printf '%s\n' "run_$RUN_ID" > "$ROOT/experiment_records/LATEST_TABLE11.txt"

echo "All output-checked Table 11 experiments completed: $RUN_DIR"
