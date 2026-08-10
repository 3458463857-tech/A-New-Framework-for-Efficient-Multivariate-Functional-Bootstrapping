# Reproducibility notes

The implementation for Section 3 is not included in this release and will be
open-sourced in a later update. The commands below concern the released Section
4 and expanded applicable-function experiments.

## Section 4 reference checks

From the repository root, run:

```text
python chapter4_compression/generate_table11_records.py
python chapter4_compression/examples.py
python -m unittest discover -s tests -v
```

The generator writes the exact Table 11 representations to
`chapter4_compression/records/`. The lower-median record includes simulated-
annealing seed `20260810`, its trace, and a full-domain certificate. The other
three rows use explicit count representations. The tests also exhaustively
verify that the final benchmark's three-variable packing preserves every inner
sum.

## Table 11 cryptographic benchmark

The retained experiment used the following environment:

- Intel Core i7-14700, 20 cores / 28 threads, 24 GB physical RAM;
- Microsoft Windows 11 host;
- Ubuntu 24.04.3 LTS under WSL2, kernel
  `6.6.87.2-microsoft-standard-WSL2`;
- Python 3.12.3, Rust 1.96.0, Cargo 1.96.0, and TFHE-rs 0.8.7.

Rerun it with:

```text
bash scripts/run_ubuntu_experiments.sh 30
```

The script regenerates the representations, runs the Section 4 tests, builds
the locked Rust benchmark, performs five warm-ups, and records 30 timed
evaluations for each row. Every result is decrypted and checked. The timed
region contains online homomorphic evaluation only; key generation, LUT
generation, input encryption, and output decryption are excluded.

The accepted record is `experiment_records/run_20260810T052530Z/`. Its
`table11.log` is the raw output, `table11_runs.csv` contains every timed input,
`table11_summary.csv` contains the descriptive statistics, and `summary.json`
is the machine-readable summary used by the revised Section 5.

## Expanded applicable-function study

Run:

```text
python expanded_function_study/run_experiments.py
python expanded_function_study/compare_intermediate_routes.py
python expanded_function_study/verify_reported_tables.py
```

The first program exhaustively evaluates 76 parameterized candidates. The
second checks 59 explicit intermediate-value alternatives and deliberately
assigns zero LUT-record cost to ciphertext additions and multiplications used
by the competing route. The report retains a row only when the proposed route
is exact, compresses the direct table by at least a factor of two, and uses
strictly fewer LUT records than that optimistic alternative.

The base results and intermediate-route results each include a separate rerun.
Stable scientific fields match row by row. These experiments measure structural
LUT-record equivalents; they are not cryptographic timing measurements.
