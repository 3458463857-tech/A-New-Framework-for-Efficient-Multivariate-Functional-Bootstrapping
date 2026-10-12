# Section 3 Algorithm 1 Reproduction

This folder provides a standalone, output-checked reproduction of the
non-negative integer-division construction in Section 3, Algorithm 1, for
`t = 16`, `t = 32`, and `t = 64`.

The implementation encrypts both inputs, evaluates the two rounded logarithmic
transforms, performs encrypted subtraction, and evaluates the outer quotient
function through small programmable-bootstrapping circuits. It does not call
TFHE-rs encrypted division and does not select the result through a cleartext
branch. Every timed result is decrypted and compared with the cleartext
quotient.

## Requirements

- Ubuntu x86-64 under WSL2 or native Windows 11;
- Rust 1.96.0 through `rustup`;
- Python 3;
- network access for the first Cargo dependency download.

Exact Rust dependencies are pinned by `Cargo.lock`; TFHE-rs is pinned to
version 0.8.7.

## Reproduce `t = 16`

On Ubuntu or WSL2:

```bash
export RAYON_NUM_THREADS=8
bash scripts/run_ubuntu.sh --samples 30
```

On Windows PowerShell:

```powershell
$env:RAYON_NUM_THREADS = "8"
powershell -ExecutionPolicy Bypass -File scripts/run_windows.ps1 --samples 30
```

## Reproduce `t = 32` and `t = 64`

On Ubuntu or WSL2:

```bash
export RAYON_NUM_THREADS=12
bash scripts/run_larger_domains_ubuntu.sh 32 --samples 30
bash scripts/run_larger_domains_ubuntu.sh 64 --samples 30
```

Each command first performs an independent exhaustive plaintext check. The
encrypted run must end with `ENCRYPTED_SUMMARY,PASS`.

## Files

- `src/main.rs`: final `t = 16` implementation.
- `src/bin/algorithm1_small_parameter.rs`: final `t = 32,64` implementation.
- `reference/verify_algorithm1.py`: independent exhaustive `t = 16` audit.
- `reference/verify_larger_domains.py`: independent exhaustive `t = 32,64`
  audit.
- `scripts/`: Ubuntu, WSL2, and Windows entry points.
- `experiment_records/run_20260816_table10/`: final output-checked timing
  records used in the manuscript.
