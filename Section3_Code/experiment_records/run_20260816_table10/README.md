# Section 3 Timing Records for the Division Table

All three records were produced on the same physical desktop: Microsoft
Windows 11, Intel Core i7-14700, 20 physical cores, 28 logical processors, and
24 GB RAM. The `t = 16` run used Ubuntu 24.04 under WSL2 with eight Rayon
workers. The `t = 32` and `t = 64` validation runs used native Windows 11 with
12 Rayon workers. All runs used Rust 1.96.0, TFHE-rs 0.8.7, and release builds.

Each record contains 30 encrypted evaluations. Every output was decrypted and
checked against the cleartext quotient. Key generation, encryption, and
decryption are outside the reported online timer.

| Parameter | Record | PBS per case | Mean online time | Paper value |
| --- | --- | ---: | ---: | ---: |
| `t = 16` | `table10_t16_30_runs_ubuntu_wsl.log` | 41 | 221.248942 ms | 221.25 ms |
| `t = 32` | `table10_t32_30_runs_windows.log` | 101 | 593.430483 ms | 593.43 ms |
| `t = 64` | `table10_t64_30_runs_windows.log` | 190 | 1226.251213 ms | 1226.25 ms |

The final line of every log is an `ENCRYPTED_SUMMARY,PASS` line. The `t = 32`
and `t = 64` records additionally report the input-transform, subtraction, and
outer-function timing breakdown for every repetition.
