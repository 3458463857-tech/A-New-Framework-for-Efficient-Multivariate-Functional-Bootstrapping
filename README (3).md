# TFHE-rs Table 11 benchmarks

`bench_table11.rs` evaluates all four Table 11 instances. It loads the exact
Section 4 inner-table records from
`chapter4_compression/records/table11_representations.csv`, reconstructs and
exhaustively verifies the outer LUT before key generation, performs five
warm-ups, and decrypts and checks every timed output.

```text
cargo run --release --locked --bin bench_table11 -- \
  ../chapter4_compression/records/table11_representations.csv 30
```

The dependency is pinned to TFHE-rs 0.8.7. Key generation, LUT generation,
input encryption, and output decryption are excluded from the timed region.
The timed region includes all required inner PBS calls, additions, and the
outer PBS. The unified benchmark uses `PARAM_MESSAGE_6_CARRY_0_KS_PBS`, whose
plaintext space is `[64]`. In the three non-binary cases, each group of three
inputs is packed in base `t` as `x0 + t*x1 + t^2*x2`; one packed inner LUT
returns the sum of the corresponding three coordinate representations. Hence
the six-variable cases use two packed inner PBS calls and one outer PBS. The
binary Hamming-weight case uses affine additions and one outer PBS.
