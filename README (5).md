# Section 4: additive LUT compression

The code distinguishes two cases that should not be conflated.

## Explicit low-span constructions

When a function depends on a small additive statistic, use the explicit inner
tables instead of a heuristic:

- `indicator_representation`: symbol counts, exact-k, thresholds, intervals,
  majority, quorum, and voting rules;
- `hamming_distance_representation`: distance balls and mismatch budgets against
  a public template;
- `weighted_representation`: bounded public weighted scores and quantized
  linear-threshold rules.

For a symbol-set count, `p_i(x_i)=1[x_i in A]`, the span is exactly `ell` and the
outer LUT has `ell+1` reachable inputs.  This construction is used for the
corrected threshold rows in the manuscript.

## Heuristic search

`anneal` implements the merge, aggregation, and perturbation moves.  Every
candidate is checked by full enumeration; a representation is never reported
as valid after a sampled-only check.  The returned solution is deterministic for
a fixed seed.

For the symmetric lower-median instance used in Table 11,
`anneal_symmetric` permits collision-penalized intermediate states and performs
an independent exhaustive verification before returning. This avoids trapping
the search at the injective base encoding. Generate the exact benchmark records
with:

```text
python generate_table11_records.py
```

The command writes `records/table11_representations.json`, including the seed,
search trace, final inner tables, outer table, and exhaustive certificate, plus
a flat CSV consumed directly by the Rust benchmark. The Hamming and two
symbol-set cases use their exact count representations; only the non-binary
median case requires the simulated-annealing record.

```text
python examples.py
```

The universal representation theorem does not imply compression.  Mode, median,
and order statistics for non-binary alphabets should be evaluated parameter by
parameter.  Pseudorandom tables and bit-mixing functions are expected to retain
large spans; `activation_bit` is included as a counterexample.
