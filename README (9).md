# Intermediate-route comparison

Regenerate this directory from `expanded_function_study/` with:

```text
python compare_intermediate_routes.py
```

`intermediate_routes.csv` contains one row for every comparison, including the
14 rejected functions. `our_records` is the paper-route LUT-record count;
`alternative_records` is the explicit competing route. `our_lut_evals` and
`alternative_lut_evals` count functional-bootstrap LUT evaluations, not circuit
depth. Intermediate ciphertext multiplications are shown separately and are
assigned zero LUT records, deliberately favouring the competitor.

A row is retained only if its full finite domain is exact,
`direct_records / our_records >= 2`, and
`our_records < alternative_records`.
