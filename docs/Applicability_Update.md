# Applicability guidance and evidence

Updated 14 October 2026.

The Function Catalogue and Supplementary Notes now make the existing evidence
easier to use when considering a new function. This is a documentation update,
not a new experiment or a new theoretical claim.

- The catalogue distinguishes 45 structural records (O), 21 measured task
  configurations (T), and eight construction families (F). Their total of 74
  is not a count of distinct function types or successful accelerations.
- Applicability labels describe whether a direct low-span candidate is available
  or a construction must be checked for the particular domain. They are empirical
  guidance, not a complete classification theorem.
- A logical-record ratio is not a measured speedup or a physical-memory ratio.
  Multistep construction counts are identified separately. Slower measured
  configurations remain included.
- The workflow is to specify the function and domain, check a candidate
  representation, count all required tables, check the evaluator's input ranges
  and correctness conditions, and then measure the complete online route.
- Possible combinations with improved LUT evaluators have not been evaluated.

The 84 measured table entries, four explicitly unmeasured entries, original
source code, parameters, inputs, and raw records are unchanged. The additional
CSV columns explain existing catalogue entries; their original numerical fields
are preserved. `functions/summarize_catalogue.py --check` validates the two
summary files using the existing catalogue only.

The root `TABLE_INDEX.csv` and `TABLE_INDEX.json` remain the selectors for final
reported timings. `SHA256SUMS.txt` and `SHA256SUMS.json` cover this release;
`docs/provenance/applicability_update.json` records the changed documentation.
Historical copies in older repository layouts do not supersede this index.
