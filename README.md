# Table 11 experiment records

The retained successful experiment is:

`run_20260810T052530Z/`

It is the final three-variable-packing implementation. The Hamming-weight row
uses one outer PBS. Each of the other three rows packs the six inputs into two
groups of three, applies two packed inner PBS calls, and then applies one outer
PBS, for three PBS calls in total.

Important files in the run directory are:

- `environment.txt` and `environment_kv.txt`: Windows 11/WSL2 runner details;
- `table11.log`: raw output-checked results for all repetitions;
- `table11_runs.csv`: normalized per-repetition records;
- `table11_summary.csv` and `summary.json`: final statistics;
- `table11_representations.csv` and `.json`: frozen representation inputs;
- `table11_representation_generation.log`: generation and verification trace;
- `cargo_tree.txt`: locked Rust dependency tree.

To create a new output-checked run:

```text
bash scripts/run_ubuntu_experiments.sh 30
```

Only Table 11 is handled by this runner. The implementation for Section 3 will
be released separately in a later update.
