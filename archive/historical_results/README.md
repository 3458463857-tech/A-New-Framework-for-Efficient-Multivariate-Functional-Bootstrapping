# Historical materials

**Historical records only. Not used for final reported results.**

Use the root `TABLE_INDEX.csv` for the final timing comparisons. This archive
preserves superseded runs, early implementations, and the earlier public
repository. A frozen file may call itself “final”; that label refers to its
original context and does not select a current paper result.

| Directory | Contents |
| --- | --- |
| `previous_public_release/` | Earlier public code, input data, results, and application examples. |
| `records/` | Earlier benchmark collections and package metadata. |
| `experiments/` | Superseded attempts separated from the active experiment groups. |
| `embedded_records/` | Earlier measurements that were bundled inside source trees. |
| `report_tools/` | Original report-generation utilities, retained as historical source only. |

Do not run archived release/report generators as the current reproduction
procedure. Some generate old document titles or Chinese text; their source
bytes are preserved to retain the historical code. The current documentation
and catalogue are English and are linked from the root README.

Shared definitions, inputs and offline checks still needed by the current
material are under `experiments/supporting_materials/`, rather than here.
Some older implementation source is restored as a dependency by the workspace
preparation tool; this does not make its historical timings current results.
Original source and logs can contain old directory names and machine paths.
