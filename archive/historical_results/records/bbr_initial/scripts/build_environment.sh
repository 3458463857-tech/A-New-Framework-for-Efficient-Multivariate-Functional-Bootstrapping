#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG=${1:-"$ROOT/results/build_$(date -u +%Y%m%dT%H%M%SZ)"}
if [[ -e "$LOG" ]] && [[ -n "$(ls -A "$LOG")" ]]; then echo 'Refusing nonempty build-log directory' >&2; exit 2; fi
mkdir -p "$LOG"
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$ROOT/.build"
cd "$ROOT/source/author/bench/HLUT-rs"
cargo +1.96.0 build --release --locked --bin matched_tasks > "$LOG/build_adapter_stdout.log" 2> "$LOG/build_adapter_stderr.log"
python3 -m venv --without-pip "$ROOT/.venv"
curl -L --fail https://bootstrap.pypa.io/get-pip.py -o "$LOG/get-pip.py" > "$LOG/pip_download.log" 2>&1
"$ROOT/.venv/bin/python" "$LOG/get-pip.py" > "$LOG/pip_bootstrap_persistent.log" 2>&1
"$ROOT/.venv/bin/python" -m pip install numpy==2.2.6 pandas==2.3.0 galois==0.4.6 click==8.3.2 maturin==1.9.4 > "$LOG/python_deps_stdout.log" 2> "$LOG/python_deps_stderr.log"
cd "$ROOT/source/author/decomposer"
VIRTUAL_ENV="$ROOT/.venv" PATH="$ROOT/.venv/bin:$PATH" RUSTUP_TOOLCHAIN=1.96.0 "$ROOT/.venv/bin/maturin" develop --release > "$LOG/build_decomposer_stdout.log" 2> "$LOG/build_decomposer_stderr.log"
"$ROOT/.venv/bin/python" -m pip freeze > "$LOG/python_requirements_resolved.txt"
