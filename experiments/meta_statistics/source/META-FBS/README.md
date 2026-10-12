## Meta-PBS
This implementation for Meta-PBS is based on [TFHE-go](https://github.com/sp301415/tfhe-go/tree/2369903).

The results for EBS, Meta-PBS, and the tree-based method can be reproduced using 
```shell
go test -benchtime=1000x -timeout=2h -run=^$ -bench ^NameofTheBenchMark$ ./tfhe
```
The available benchmarks include
+ BenchmarkPBSwithEBS: EBS with $\log_2(t)=8,9,10$
+ BenchmarkPBSwithEBS2: EBS with $\log_2(t)=10,11$, recommended to run with 100 iterations
+ BenchmarkMetaFBS: negacyclic Meta-PBS with $\log_2(t)=8,9,10,11,12$
+ BenchmarkMetaUint8Compact: 8-bit Meta-WoPPBSManyLUTs, corresponding to the Meta_8C parameter set
+ BenchmarkMetaUint8: 8-bit Meta-WoPPBSManyLUTs, corresponding to the Meta_8 parameter set
+ BenchmarkTreeBased: timings for blind rotation & public functional key switching in the 8-bit tree-based method [[TBC+25](https://doi.org/10.46586/tches.v2025.i2.535-578)]
+ BenchmarkLHEBase256: timing for Extr.+Refr. in the 8-bit single-ciphertext integer-input Refined LHE [[WHS+25](https://dl.acm.org/doi/abs/10.1145/3719027.3744873)]
+ BenchmarkNTS25: timings for blind rotation & sampleextract+keyswitch & packingks in the 12-bit negacyclic LargeLUT [[NTS25](https://dl.acm.org/doi/abs/10.1145/3719027.3744808)]

There are also benchmarks targeting failure probablities less than $2^{-128}$, including
+ BenchmarkMetaFBS128
+ BenchmarkMetaUint8Compact128
+ BenchmarkMetaUint8Compact128

The parameter selection functions include
+ TestMetaFBSFindParams128
+ TestMetaFBSFindParams64
+ TestMetaWoPPBS8n8C_128
+ TestMetaWoPPBS8n8C_40
+ TestNTS25FindParams64

The obtained parameters for EBS and Meta-PBS(or Meta-WoPPBSManyLUTs) are partly hardwired in the benchmarks.
The value of $c_\mathrm{Hom}$, $c_\mathrm{Meta}$, and $r_\mathrm{ext}$ are found using `tfhe.SweepParameterAuto` and hardwired in the benchmarking code and params_list.go, while the other parameters are found using `tfhe.SweepParameter` during runtime.

The capacity analysis and timings for Refined LHE can be reproduced using [refined-tfhe-lhe](https://github.com/KAIST-CryptLab/refined-tfhe-lhe/tree/9b0426e), with the following modifications
+ In `error_analysis/param.sage`, use 
  ```python
  stddev_953 = 2.65690503739331e-7
  ...
  stddev_2048 = 7.63220286136280e-16
  ```
+ Use the following toolchain to avoid compilation errors
```shell
rustup toolchain nightly-2024-09-01
rustup override set nightly-2024-09-01
```
+ Mofify the implementation of `keyswitch_lwe_ciphertext` in tfhe-rs by adding the following line to L.158 of `lwe_keyswitch.rs`. This will produce timings for Refined LHE as if it used the shared-randomness secret [[BCL+24](https://dl.acm.org/doi/abs/10.1145/3658644.3670376)] as tfhe-go does.
  ```rust
  .skip(lwe_keyswitch_key.input_key_lwe_dimension() - lwe_keyswitch_key.output_key_lwe_dimension())
  ```

Finally, run `error_analysis/integer_input_lhe.sage` to get the capacity of `improved_wopbs_4_4`.
Run `cargo bench --bench bench_integer_input_lhe --features=nightly-avx512` to get the timings of `INT_LHE_BASE_256`.

Note that the timings from `BenchmarkLHEBase256` in TFHE-go should be used for Extr.+Refr. when calculating the total time of the parameter set LHE_8.
