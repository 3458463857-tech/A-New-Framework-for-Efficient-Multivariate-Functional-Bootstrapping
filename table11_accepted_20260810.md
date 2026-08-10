# Accepted Table 11 rerun (2026-08-10)

These are the Table 11 values to be used in the next revision of Section 5. The
source run is `run_20260810T052530Z`. Each reported mean is based on 30 online
evaluations. Every timed output was decrypted and checked; key generation, LUT
generation, input encryption, and output decryption were excluded from the
timed region.

The last three functions use base-\(t\) packing in groups of three variables,
so their measured programmable-bootstrapping call count is three rather than
seven.

| Function | Calls | Mean (ms) | Std. dev. (ms) | Median (ms) | Min. (ms) | Max. (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Hamming-weight interval | 1 | 92.459701 | 1.144599 | 92.460434 | 90.314544 | 94.422509 |
| Symbol-set interval | 3 | 277.384139 | 5.429005 | 276.509138 | 270.382128 | 300.257256 |
| Symbol-set threshold | 3 | 275.992643 | 3.357248 | 275.426841 | 272.042326 | 291.153552 |
| Lower median | 3 | 274.932895 | 2.522332 | 274.302002 | 271.926284 | 282.399639 |

The authoritative machine-readable record remains
`run_20260810T052530Z/summary.json`.
