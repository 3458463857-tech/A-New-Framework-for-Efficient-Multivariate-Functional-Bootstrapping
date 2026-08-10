# Expanded applicable-function study

This directory is the source of every new number in `applicable_functions.pdf`.
It contains a deterministic plaintext experiment rather than a ciphertext-time
benchmark.

## What is measured

For every listed finite function, the script enumerates the full Cartesian
domain and compares a direct evaluator with the stated decomposed evaluator.
It records:

- direct records: one record per original input tuple;
- decomposed records: consecutive unary-LUT record-equivalents used by the
  decomposition (repeated calls are counted conservatively unless stated);
- LUT evaluations, reachable intermediate states, output cardinality, number of
  exhaustive cases, and maximum output error;
- the quantization scale for the finite-domain logarithmic constructions.

The compression ratio is `direct_records / decomposed_records`. A function is
retained in the note only when the full-domain check is exact and this ratio is
at least `2.0`. The raw files retain screened-out cases so that negative results
are not hidden.

These counts do **not** include TFHE parameter selection, ciphertext noise,
key switching, memory traffic, or measured PBS latency. They therefore support
structural LUT-compression claims only, not ciphertext speedup claims.

## Reproduce

From this directory, with Python 3.11 or later:

```text
python run_experiments.py
```

No third-party Python package is required. The command rewrites:

- `results/all_results.csv`: flat table used for checking the PDF;
- `results/results.json`: environment metadata plus retained and screened-out
  records.

The reference run used in the revised PDF was performed on 2026-08-06. It
evaluated 76 parameterized candidates; 45 passed the mechanical exactness and
2x selection rule. The PDF then omits three mechanically retained but
deliberately trivial affine/sum examples. Every displayed maximum error is zero.

The deeper elementary-function rows use 80- and 110-digit decimal reference
evaluations. Both precisions must give the same integer output on every input.
This includes the screened sine, cosine, tangent, and hyperbolic ratios, so their
negative compression results are reproducible rather than anecdotal.

## Intermediate-value alternatives

Run:

```text
python compare_intermediate_routes.py
```

This second program checks 59 explicit comparisons and writes
`intermediate_routes/intermediate_routes.csv` and `.json`. It covers all 19
elementary rows, every function formerly shown in Section 5, and additional
order/histogram examples used to keep the revised table informative.

The alternative is deliberately optimistic. Ciphertext additions and
ciphertext multiplications used to form a product, power sum, moment, or
similarity count are recorded but assigned zero LUT records. Comparator and
equality LUTs needed to form sorted or histogram states are counted for both
routes. A row is retained only when it is exact on the complete finite domain,
`direct_records / our_records >= 2`, and `our_records < alternative_records`.
The reference output contains 59 comparisons: 45 retained (19 elementary and
26 further functions) and 14 screened out.

`verification_rerun/` contains a second complete run. All scientific CSV
fields were identical row by row; only the elapsed-time field was excluded from
the comparison.

## Interpretation

The study starts from the paper's central many-to-one observation: the output
range is often much smaller than the Cartesian input domain. The experiments
then test the second, implementation-relevant question: whether the output
classes can be reached through a low-span sufficient statistic, a shallow
elementary composition, a comparator network, or a bounded dynamic program.
A small output range by itself is not a proof of a small implementation; the
screened trigonometric ratios and high-interaction Boolean control make that
distinction explicit. The PDF uses the exact function name and parameter string
from `all_results.csv`, which uniquely identify the executable definition for
every table row.
