# Table 11 representation records

`table11_representations.json` is the complete machine-readable structural
record consumed by the Table 11 Rust benchmark. It includes each inner row, the
outer LUT on every reachable sum, the number of exhaustively checked inputs,
and the verification result.

For the lower-median row, `search` additionally records the deterministic
simulated-annealing seed (`20260810`), configured iteration and restart limits,
actual iterations and restarts executed before the target span was reached,
initial row, accepted move, and improvement trace. The CSV is the normalized
form read by `tfhe_rs/src/bin/bench_table11.rs`.

Regenerate both files from the artifact root with:

```text
python chapter4_compression/generate_table11_records.py \
  --output-dir chapter4_compression/records
```
