# Quotient failure: a localized cause and a successful parameter repair

The t16 quotient is now reproducible with the BBR author evaluator. The common
five warm-ups and thirty measured cases all passed after changing only the PBS
decomposition from `(base_log, levels) = (29, 1)` to `(15, 2)`. The thirty-case
mean is **2729.538173 ms**, with population SD **33.646789 ms** and median
**2722.399114 ms**. This result must be named **BBR author evaluator, revised PBS
decomposition**. It is not a measurement under the unmodified author CSV row.

## What was already correct

The retained fixed-seed search produced a rank-256 representation with 25 atomic
LUTs and 11 products. Its exact field computation agrees with the target on all
256 input points, including the 240 legal quotient inputs and sixteen padded
zero-divisor inputs. The input ordering is `m + 16*d`. Both operands are
independently encrypted with `Encoding::new_trivial(17)`; the result uses the
canonical F17 representatives 0 through 15. These choices agree with the author
evaluator. Multiplication uses the valid F17 identity
`xy = ((x+y)^2 - (x-y)^2)/4`, with inverse-of-four equal to 13.

The original failed run returned 4 for `(m,d)=(0,15)`. It did not retain its
intermediate ciphertexts or secret key. The new diagnostic generated a fresh
key, repeated that same input and configuration, and returned 14. Thus the
following is a directly observed failure mechanism in a new reproduction;
it is not a retrospective measurement of the discarded original ciphertexts.

## Where the new failure first occurred

`results/division_diagnostic_attempt1/stages.jsonl` records every linear input,
atomic output, multiplication branch and final output. The diagnostic's final
ciphertext was **bitwise identical** to a second call to the unchanged author
`partial_lut_evaluation` on the same encrypted inputs and key. This cross-check
guards against a diagnostic-only algebra or ordering error.

Both original encrypted inputs and atomic outputs numbered 0 through 4 decoded
correctly. The first wrong value was the weighted input of atom 5, before any
of the eleven multiplication subroutines. Its coefficients are

```
[0, 5, 13, 1, 15, 7, 14]
```

The first two positions refer to the fresh operands. The errors of the next
five ciphertexts, expressed in F17 grid spacings, were

```
e0 = +0.01832595167547879
e1 = -0.01194392940283251
e2 = +0.01654613180880915
e3 = -0.0002437059913233952
e4 = +0.03510662488417893
```

Their weighted error is

```
13*e0 + e1 + 15*e2 + 7*e3 + 14*e4
  = +0.9642722259497702.
```

The correct grid point is 12. The observed position is therefore
`12.96427222594977`, which rounds to **13**, not 12. The weighted-error prediction
and observed coordinate agree to the precision of the diagnostic. In torus
units the error is `0.05672189564410413`, beyond the half-spacing `1/34`.
This directly identifies accumulation of existing ciphertext errors as the
cause of this first wrong intermediate value. It is not an inference based
only on the selected nu label.

The author `measure_noise` routine measures a residual around the **nearest**
decoded point, not around the desired value, and returns it with an extra
factor p relative to torus units. We did not use that residual alone to judge
correctness. The analysis combines its sign and scale with the independently
decoded and expected field values. All five preceding outputs were still
correct; their residuals can therefore be summed around their known correct
points. The recorded coordinates are floating-point reconstructions, not
exact integer phase dumps. Full per-stage values, the reconstruction rule and
the reproducible numerical check are in `division_root_cause_attempt1/`.

For a separate LUT control, the atom-6 LUT was applied under the same key to
all seventeen freshly encrypted field elements and all seventeen zero-mask
LWE encodings. All **34/34** outputs were correct. The encoding and LUT mapping
are consequently not the source of that observed chained-input failure.

## What changed, and what did not

| Parameter | Failed configuration | Repaired configuration |
|---|---:|---:|
| Small LWE dimension | 849 | 849 |
| GLWE dimension / polynomial size | 1 / 4096 | 1 / 4096 |
| LWE standard deviation | 1.6512448356449926e-6 | unchanged |
| GLWE standard deviation | 2.168404344971009e-19 | unchanged |
| KS base log / levels | 4 / 4 | unchanged |
| PBS base log / levels | 29 / 1 | **15 / 2** |
| Plaintext field | F17 | F17 |
| Logical PBS calls | 47 | 47 |

A smaller decomposition base reduces the sizes of digits multiplying noisy
encrypted key components in PBS, while a second level retains adequate
decomposition precision (30 represented bits versus 29). This is the reason
for testing this particular change. The experiment establishes that the
combined PBS-output error was reduced sufficiently for this computation.
It does **not** separately identify contributions from encrypted-key noise,
decomposition rounding and Fourier numerical error, or establish a theoretical
reduction factor for their sum.

For the same plaintext diagnostic input, with a fresh key for each
configuration, representative observed errors were:

| Quantity, in F17 grid spacings | Original 29x1 | Revised 15x2 |
|---|---:|---:|
| Atom 0 output error | +0.0183259516755 | +0.000002239105637 |
| Atom 4 output error | +0.0351066248842 | +0.000004968628103 |
| Atom 5 weighted-input error | +0.964272225950 | +0.000173977544527 |
| Final output error relative to expected, centered mod17 | -2.65391090020 | +0.000107615759250 |

Every stage of the revised diagnostic passed, including both branches of all
eleven products and the final linear combination. Its ciphertext was again
bitwise identical to the unchanged author evaluator at the same parameters.
The original literal `left + 16*right` operation and terminal output combination
were preserved. No additional refresh was introduced.

## Independent production timing

The production binary `matched_division_pbs15x2` contains only two additional
parameter assignments relative to the original measurement adapter, plus
explanatory comments. The exact diff is retained. It calls the original author
evaluator with **no intermediate decryptions**. The measured interval includes
all 25 atoms, 22 product PBS calls, linear combinations, online LUT encodings,
accumulator preparation and output production. Key generation, input
encryption, output decryption, offline decomposition and logging are outside
the interval, as for the other published rows. Every actual input remains in
the common manifest; no sample was discarded or replaced.

- Successful run and exact source snapshots:
  `results/division_fhe_pbs15x2_attempt1/`.
- Statistics, complete parameters and source/input/data hashes:
  `summary/division_pbs15x2_attempt1/results.json` and `results.csv`.
- Original failure, retained unchanged: `results/division_fhe_attempt1/`.
- Diagnostic original and revised runs:
  `results/division_diagnostic_attempt1/` and
  `results/division_diagnostic_pbs15x2_attempt1/`.
- Numerical analysis and benchmark source diff:
  `evidence/division_root_cause_attempt1/`.

The original CSV's failure label is **not** assigned to the revised parameters.
Concrete security and whole-computation failure probability have not been
re-estimated for this configuration. Thirty-five successful encrypted cases
are empirical correctness evidence, not a proof of a small failure tail.
The exact certificate is unchanged and remains valid over the entire domain.

## Reproduction

In the prepared Linux/WSL environment, with Cargo dependencies already fetched,
use a fresh output directory for every command:

```bash
bash scripts/run_division_diagnostic.sh "$PWD/results/diagnostic_new_original" original
bash scripts/run_division_diagnostic.sh "$PWD/results/diagnostic_new_revised" pbs15x2
bash scripts/run_division_fhe_pbs15x2.sh \
  "$PWD/results/division_search_fixed_attempt1" \
  "$PWD/results/division_fhe_pbs15x2_new"
```

The searched certificate is already retained; reproducing this measurement
does not require rerunning the Python decomposition search. The diagnostic
and production runners refuse existing output directories. The two analysis
scripts under `scripts/` audit the named published attempts and also refuse
existing evidence/summary output directories; run them in a fresh working copy
or adapt their input/output constants with an explicitly saved diff when
analyzing a new run. Keep the successful and failed runs together.
