# Revised English Section 5

- `第五章.tex` is the complete English Section 5 fragment.
- `experiment_values.tex` records the accepted Table 11 run identifier,
  environment, repetition count, and four measured means.

The fragment contains only the section body and assumes the packages,
bibliography entries, notation, and `\Z` macro from the main manuscript. From
the repository root, include it with `\input{section5/第五章.tex}`.

Running `bash scripts/run_ubuntu_experiments.sh 30` creates a new checked record
and refreshes `experiment_values.tex` only after all four Table 11 rows pass.
