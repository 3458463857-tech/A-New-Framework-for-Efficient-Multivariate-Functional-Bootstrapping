# A New Framework for Efficient Multivariate Functional Bootstrapping

This repository contains the currently released implementation and reproducibility materials for the Section 4 decomposition framework, together with an auxiliary catalogue of applicable functions. The implementation for Section 3 is not included in this release and is planned for a later update.

All documents, source files, comments, filenames, and reproduction instructions in this release are in English.

## Repository layout

The repository root intentionally contains only three entries:

- `Application_function.pdf`: a human-readable catalogue of selected function types and finite-domain compression experiments. Section 4 of that document concerns functions applicable to the paper's Section 3 scheme, and Section 5 concerns functions applicable to the paper's Section 4 scheme.
- `Section4_Code/`: all released code, tests, benchmark inputs, retained records, and auxiliary experiment programs.
- `README.md`: this consolidated description and reproduction guide.

No manuscript section, LaTeX source, or TeX-generated value file is included in this release.

## Contents of `Section4_Code`

- `chapter4_compression/` implements explicit low-span constructions, deterministic simulated annealing, exhaustive verification, and generation of the four benchmark representations.
- `chapter4_compression/records/` contains the exact CSV and JSON representations consumed by the encrypted benchmark.
- `tfhe_rs/` contains the output-checked TFHE-rs 0.8.7 benchmark. The binary Hamming-weight case uses one outer PBS. Each of the other three cases packs six inputs into two groups of three and uses two packed inner PBS calls followed by one outer PBS.
- `tests/` contains the Section 4 regression tests, including exhaustive verification of the three-variable packing.
- `scripts/` contains the Ubuntu/WSL2 benchmark runner and the CSV/JSON summarizer.
- `experiment_records/run_20260810T052530Z/` preserves the accepted 30-repetition run, including the environment, dependency tree, raw per-repetition output, frozen representations, checksums, normalized CSV files, and machine-readable summary.
- `application_function_study/` contains the deterministic finite-domain programs and retained raw records used by `Application_function.pdf`. It also preserves independent reruns of the base study and the intermediate-route comparison.
- `LICENSE` is the MIT license for the original code. Dependencies remain under their own licenses.

## Requirements

The plaintext reference checks and the applicable-function study require Python 3.11 or later and use only the Python standard library.

The encrypted benchmark additionally requires Ubuntu or WSL2, Bash, Rust, Cargo, and `sha256sum`. The Rust dependency is pinned by `Cargo.lock` to TFHE-rs 0.8.7.

## Quick start

Run the following commands from `Section4_Code/`:

```bash
python3 chapter4_compression/generate_table11_records.py \
  --output-dir chapter4_compression/records
python3 chapter4_compression/examples.py
python3 -m unittest discover -s tests -v
```

These commands regenerate and exhaustively verify the structural representations. The lower-median record uses deterministic simulated annealing with seed `20260810`; the other three cases use explicit count representations.

To regenerate the applicable-function records:

```bash
python3 application_function_study/run_experiments.py
python3 application_function_study/compare_intermediate_routes.py
```

The base study evaluates 76 parameterized candidates and retains 45 under the rule “exact full-domain result and at least 2x direct-table compression.” The intermediate-route comparison checks 59 rows and retains 45: 19 elementary rows and 26 further functions. Ciphertext additions and multiplications used by the competing route are assigned zero LUT-record cost, deliberately favoring that alternative. These experiments report structural LUT-record counts, not ciphertext timing.

## Output-checked encrypted benchmark

From `Section4_Code/` under Ubuntu or WSL2, run:

```bash
bash scripts/run_ubuntu_experiments.sh 30
```

The runner regenerates the four representations, executes the Section 4 tests, builds the locked Rust benchmark, performs five untimed warm-ups, and records 30 timed evaluations for each function. Every result ciphertext is decrypted and checked after the timer stops. Key generation, LUT generation, input encryption, and output decryption are excluded from the timed region.

The retained run is `experiment_records/run_20260810T052530Z/`. Its mean online times are 92.459701 ms, 277.384139 ms, 275.992643 ms, and 274.932895 ms, with PBS-call counts 1, 3, 3, and 3, respectively. The authoritative details are in `summary.json`, `table11_runs.csv`, and the raw `table11.log`.

## Interpreting the auxiliary study

Every displayed finite-domain result in `Application_function.pdf` is exact for its stated inputs and retains a structural advantage over the stated intermediate-value route. The rejected rows remain in the machine-readable records. A small output range motivates compression, but does not by itself prove that an efficient decomposition exists; parameter growth, ciphertext noise, key switching, memory traffic, and parallelism are outside these structural record counts.
