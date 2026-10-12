#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required for the independent reference check." >&2
  exit 2
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "ERROR: Rust/Cargo is required. Install the toolchain declared in rust-toolchain.toml." >&2
  exit 2
fi

python3 reference/verify_algorithm1.py

if [[ -z "${RAYON_NUM_THREADS:-}" ]]; then
  export RAYON_NUM_THREADS=8
fi
echo "RUN_ENV,RAYON_NUM_THREADS=${RAYON_NUM_THREADS}"

if (($# == 0)); then
  set -- --samples 3
fi

cargo run --release --locked -- "$@"
