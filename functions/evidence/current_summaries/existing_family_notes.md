# Count-based construction families

Let each input lie in `[t] = {0,...,t-1}` and let `A` be a public subset. The indicator inner maps produce the count `S = sum_i 1[x_i in A]`. A public outer table `Q(S)` then gives a count, threshold, interval, exact-count test, parity, residue, binned output, or clipped output.

These are applications of the existing count construction, not additional encrypted experiments. The generic record count is at most `nt+n+1`; this implies compression only when that quantity is smaller than `t^n`. Affine inner maps can sometimes be omitted in an implementation. New domains and output ranges still require parameter and noise checks.

`original_functions.py` supplies count, threshold, interval, exact-count, and Hamming-ball targets. `original_compress.py` supplies `indicator_representation` and `verify`. Parity, residue, and multilevel outputs can be specified through the general outer-table interface; no separate timed ciphertext driver is claimed for them.

For a Hamming ball, the template and radius are public. The template is not an encrypted input. Majority on an even number of inputs needs an explicit tie rule.
