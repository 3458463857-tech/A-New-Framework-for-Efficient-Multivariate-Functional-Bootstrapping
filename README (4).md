# Artifact for multivariate functional bootstrapping

This directory is prepared for release with *A New Framework for Efficient
Multivariate Functional Bootstrapping*. The intended repository address is:

`https://github.com/3458463857-tech/A-New-Framework-for-Efficient-Multivariate-Functional-Bootstrapping.git`

The implementation for Section 3 is not included in this release and will be
open-sourced in a later update.

## Repository contents

- `chapter4_compression/` contains the explicit low-span constructions, the
  deterministic simulated-annealing search, exhaustive verification code, and
  the exact representations used by Table 11.
- `tfhe_rs/` contains the output-checked TFHE-rs benchmark for Table 11. The
  final code packs three small-domain variables into each inner lookup, so the
  last three rows use two inner PBS calls and one outer PBS call.
- `experiment_records/run_20260810T052530Z/` is the retained 30-repetition
  Table 11 run. It contains the environment, raw per-repetition log, generated
  representations, dependency tree, normalized CSV files, and `summary.json`.
- `expanded_function_study/run_experiments.py` is the later exhaustive study
  of shallow elementary-function compositions and other multivariate
  functions. Its base results are in `expanded_function_study/results/`, with
  an independent rerun in `expanded_function_study/verification_rerun/`.
- `expanded_function_study/compare_intermediate_routes.py` compares the
  proposed decompositions with explicit intermediate-value routes. Its records
  are in `expanded_function_study/intermediate_routes/`, with a verification
  rerun in `expanded_function_study/intermediate_routes_verification_rerun/`.
- `applicable_functions.tex` and `applicable_functions.pdf` give the
  human-readable empirical catalogue derived from those expanded experiments.
- `section5/第五章.tex` is the complete revised English Section 5 fragment.
- `tests/` contains the Section 4 regression tests, including an exhaustive
  check of the three-variable packing used by the final Table 11 code.

## Quick start

The plaintext checks use only the Python standard library:

```text
python chapter4_compression/generate_table11_records.py
python chapter4_compression/examples.py
python expanded_function_study/run_experiments.py
python expanded_function_study/compare_intermediate_routes.py
python expanded_function_study/verify_reported_tables.py
python -m unittest discover -s tests -v
```

To rerun the cryptographic Table 11 benchmark in Ubuntu under WSL2, install
Python 3 and Rust, then run from the repository root:

```text
bash scripts/run_ubuntu_experiments.sh 30
```

The runner regenerates and exhaustively checks the four representations before
timing. Every timed ciphertext is decrypted and compared with the cleartext
answer after the timer stops. Key generation, LUT generation, input encryption,
and output decryption are excluded from the online timing region.

## Retained Table 11 result

The retained run was performed on the Windows 11 desktop described in Section
5, with Ubuntu 24.04.3 LTS under WSL2 as the benchmark environment. Its means
over 30 repetitions are 92.46 ms, 277.38 ms, 275.99 ms, and 274.93 ms. The PBS
counts are respectively 1, 3, 3, and 3. Exact statistics and raw inputs are in
`experiment_records/run_20260810T052530Z/`.

The expanded applicable-function study reports structural LUT-record counts,
not ciphertext timings. Every displayed finite-domain result is exhaustively
checked, and screened-out cases remain in the machine-readable files.

## License

Original code in this artifact is released under the MIT License. Dependencies
remain under their own licenses.
