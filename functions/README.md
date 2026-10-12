# Function Catalogue and Verification Records

Start with [the English catalogue](Function_Catalogue_and_Verification_Records.pdf) to find a function's exact definition, domain and available evidence. Use [catalog.csv](catalog.csv) for the full values and source references. For reproduction commands and the final measured tables, start from the [repository README](../README.md) and [TABLE_INDEX.csv](../TABLE_INDEX.csv).

The catalogue contains **74 entries**:

| IDs | Contents | What the evidence supports |
|---|---|---|
| O01-O19 | 19 elementary composite-function instances | Stored finite-domain checks and logical LUT-record counts |
| O20-O34 | 15 order-statistic instances on six eight-valued inputs | Stored comparison-network constructions and logical counts |
| O35-O45 | 11 histogram-statistic instances on eight five-valued inputs | Stored histogram constructions and logical counts |
| T01-T17 | 17 measured count/statistic configurations | Recorded encrypted outputs and elapsed times for the specified settings |
| T18-T21 | Four integer-quotient configurations | Recorded quotient measurements; T20 is the retained supplementary `t=64` case |
| F01-F08 | Eight count-based construction families | Applications of the existing count representation, without additional encrypted measurements |

The 74 entries include 66 concrete parameter instances and eight families. Functions and domains overlap. The entry count is not a count of distinct function types or speedups.

## Files

| Path | Purpose |
|---|---|
| `Function_Catalogue_and_Verification_Records.pdf` | Reader-facing English catalogue, with definitions, examples, tables and limitations |
| `Function_Catalogue_and_Verification_Records.tex` | Editable English source; compiled with standard pdfLaTeX |
| `catalog.csv` | Complete English index, retaining the stored numerical precision and original entry IDs |
| `evidence_index.csv` | Evidence snapshots, their current repository paths and SHA-256 hashes |
| `evidence/current_summaries/` | Copies of timing summaries, function definitions and plaintext verification outputs |
| `evidence/original_study/` | Original structural-study scripts, saved CSV/JSON results and stored repeat checks |
| `evidence/Application_function_original.pdf` | Original English structural catalogue, preserved unchanged for reference |

The original PDF's directory names and statement about unreleased Section 3 code are historical. They do not describe this repository's current contents. The root README and reproduction guide give the current release status.

## Reading the CSV

- `catalog_id` is the stable entry ID used in the PDF. `function_name`, `definition_tex`, `domain`, `example_input` and `example_output` specify the exact function. The examples explain its meaning and are not additional experiments.
- `evidence_level` distinguishes a finite-domain check, an encrypted measurement and a direct-construction family.
- `logical_records` uses the convention in `record_convention`. A logical count is not physical memory or encrypted running time.
- `abstract_lut_evaluations` counts calls in the structural construction. `actual_ours_pbs` is a separate count from the measured implementation.
- `ours_mean_ms`, `bbr_mean_ms`, `refined_mean_ms`, `meta_mean_ms` and `native_mean_ms` contain only stored successful encrypted measurements. A blank means unmeasured, not zero time or an advantage. The catalogue contains 84 populated mean cells.
- `faster_than_tested_methods` lists only methods with a higher recorded mean for that row. Slower configurations are retained.
- `alternative_records` and `alternative_route` preserve the structural study's specified comparison routes. These are not BBR26 times, optimal costs or lower bounds on all implementations.
- `source` identifies the evidence file; paths are relative to `functions/`. A suffix after `#` identifies a task or row. `source_detail` adds the original table or task name.

The original scripts' `elapsed_ms` fields describe plaintext Python checks. They have not been copied into the encrypted timing columns.

## Definitions and applicability

The measured statistics use the stored program definitions: lower median, smallest-value mode tie, non-interpolated interquartile range and lower-median absolute deviation. The PDF gives their formulas and examples. Timings on ternary inputs do not apply to the structural catalogue's eight-valued or five-valued domains.

The F-series includes set-membership count, threshold/majority, interval, exact-count test, parity, residue, multilevel output and a Hamming ball around a public template. `original_functions.py` provides the count, threshold, interval, exact-count and Hamming-ball targets. `original_compress.py` provides `indicator_representation` and `verify`. Parity, residue and multilevel outputs use this general interface with a specified outer table; no dedicated ciphertext timing command is claimed for those families.

O01 counts 1192 records for the legal inner domains `64+63`. T20 counts 1193 by including a zero-divisor padding slot, `64+64`. The difference is a counting convention. The `t=8` quotient measurement reuses the `T=16, M=22` circuit; it is not claimed to be a separately optimized three-bit implementation.

## Check the saved structural records

From this directory:

```bash
python evidence/original_study/verify_records.py
```

This compares saved results and stored repeat checks; it does not rerun the original function enumeration or encrypted benchmarks. To rerun the finite-domain study, use `run_experiments.py` and `compare_intermediate_routes.py` in `evidence/original_study/`. Those programs write results, so run them in a separate working copy to preserve the supplied records. Follow the root reproduction guide for encrypted experiments.

To rebuild the catalogue PDF with TeX Live or an equivalent installation:

```bash
pdflatex -interaction=nonstopmode -halt-on-error Function_Catalogue_and_Verification_Records.tex
pdflatex -interaction=nonstopmode -halt-on-error Function_Catalogue_and_Verification_Records.tex
```

No Chinese LaTeX support is required.

## Limits of the evidence

Stored finite checks support the stated domains. High-precision numerical checks of transcendental functions are not proofs over all real inputs. Structural compression does not alone establish smaller physical memory or lower encrypted latency.

The encrypted comparisons concern the recorded hardware, implementations, encodings and parameters. The methods do not use fully aligned security parameters and overall failure probabilities. The corrected BBR quotient parameters have not had their failure probabilities recalibrated. The measurements therefore do not establish an absolute performance ranking at a common security and reliability target.

`TABLE_INDEX.csv` at repository root identifies the selected final measured records. Historical experiments are separate under `archive/historical_results/` and are not used for final reported results. The structural study retained here is supporting evidence for the catalogue, not a historical ciphertext baseline substituted into the final timing tables.
