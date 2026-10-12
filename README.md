# A New Framework for Efficient Multivariate Functional Bootstrapping

This repository contains the source code, parameter configurations, input data,
and experimental records supporting the paper of the same title. The method
uses function structure to reduce the size of a multivariate representation.
Smaller representations do not guarantee lower running time for every function
or implementation.

## Start here

1. Read [Supplementary Notes](docs/Supplementary_Notes.pdf) for the parameter
   choices, measurement protocol, and limits of the comparisons.
2. Use [TABLE_INDEX.csv](TABLE_INDEX.csv) to find the source, inputs, raw records,
   and summary for a particular reported result.
3. Read the [Function Catalogue](functions/Function_Catalogue_and_Verification_Records.pdf)
   for function definitions, representation sizes, evidence, and measured cases.
4. Follow the [Reproduction Guide](docs/Reproduction_Guide.md) to prepare a
   workspace and run a selected experiment.

## What is included

| Path | Contents |
| --- | --- |
| `experiments/` | Our programs, baseline adapters, parameter constants, inputs, raw measurements, and summaries. |
| `experiments/supporting_materials/` | Shared definitions, inputs, offline search, and finite verification records used by the current material. |
| `TABLE_INDEX.csv`, `TABLE_INDEX.json` | Final result-to-file index, including checksums and main/supplementary status. |
| `functions/` | English catalogue, editable source, data table, and supporting evidence. |
| `docs/` | Supplementary Notes, reproduction instructions, and file provenance. |
| `scripts/` | File verification, workspace preparation, and statistics reconstruction. |
| `archive/historical_results/` | Historical records only. Not used for final reported results. |

The four material categories stated in the paper are available here:

| Material | Where to find it |
| --- | --- |
| Source code | Experiment `source/`, `ours/`, and `scripts/` directories; exact measured source snapshots are indexed. |
| Parameter configurations | Supplementary Notes, source constants, and recorded run configurations; the index identifies named parameter sets where available. |
| Input data | Indexed input CSV files and saved input snapshots. |
| Experimental records | Indexed raw logs, per-run observations, and summaries. |

## Final results and historical records

The index contains **84 measured entries**: 81 main-table entries and three
supplementary entries. Four additional entries explicitly identify missing
measurements. Quotient comparisons use exact integer division; the main table
uses `t = 8, 16, 32`, with earlier `t = 64` observations retained as supplementary
results. Missing values are not filled with estimated times.

Only the files selected by the index supply a reported timing. Other retained
files include offline decompositions, correctness checks, build records, and
failure diagnostics. Superseded measurements and the earlier public repository
are separated under `archive/historical_results/`; see its README before using
them. Old labels such as “final” in a frozen log do not override the current index.

The catalogue contains 45 structural examples, 21 measured task configurations,
and eight construction families. These are different kinds of evidence, not
74 independent timing successes. Instances without a speed advantage remain
included.

## Verify and prepare

From the repository root, with Python 3.11 or newer:

```bash
python3 scripts/verify_artifact.py
python3 scripts/rebuild_statistics.py --output ../statistics_check --run-frozen-parsers
python3 scripts/prepare_workspace.py --output ../reproduction
```

These commands check files, reconstruct statistics from saved records, and
prepare a separate workspace. They do not run ciphertext experiments. The output
directories must be new. Use Linux or WSL for the experiment scripts, then follow
the Reproduction Guide for the Rust/Go dependencies and execution commands.

Frozen programs and logs retain their original path strings. Preparation restores
the compatible directory layout outside this repository and records the limited
shell-runner adjustments needed for optional build caches and an installed Go
toolchain. It does not change algorithms, parameters, inputs, or recorded results.

## Interpretation and limitations

The measurements compare implementations on the same machine, functions, and
plaintext inputs. Encodings, cryptographic parameters, and failure calibrations
are not fully unified. The results describe the tested configurations; they do
not establish an absolute ranking at matched security and whole-computation
failure probability. The adjusted BBR quotient parameters have not been
recalibrated for evaluation failure probability.

Logical LUT entries, PBS calls, memory, and online time are different quantities.
Finite correctness checks and successful measured runs do not prove a
cryptographic failure bound. Reconstructing saved statistics is also distinct
from independently rerunning the benchmarks.

## License

Original contributions use the [MIT License](LICENSE). Third-party components
retain their own terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
