# File provenance

`file_map.json` and its CSV copy connect released files to their original
locations, SHA-256 digests, and compatible execution-workspace paths. Public
paths were reorganized; source programs, input data, and raw measurements retain
their original bytes. Omitted editorial documents are not execution inputs.

The `original_path`, `archive`, and `workspace_path` fields are provenance and
compatibility identifiers. Old internal directory names in these fields or in
frozen source/logs are intentionally retained. They are not current public
repository names and do not designate a newer set of results.

The preparation tool reads this map to create a separate workspace. The root
SHA-256 manifest additionally covers the English documentation and packaging
utilities. Hash verification checks consistency; it does not rerun the science.
