# License scope and third-party software

The project authors have selected the **MIT License** for the authors' original code,
new original comparison adapters, and the new release scripts. The root
`LICENSE` applies to those contributions. Earlier README/license-policy notes
are retained as historical bytes; they do not describe this release's current
choice.

Third-party source, embedded code, modifications derived from third-party code,
and copied license notices retain their applicable upstream terms. The root MIT
License does **not** relicense those components. Source comments and the license
file beside each component take precedence for that component.

| Component | Retained terms and location |
|---|---|
| BBR/HLUT author artifact | CryptoExperts copyright and redistribution terms: `experiments/bbr/source/author_provenance/LICENSE`; the earlier full author tree is under `archive/historical_results/records/bbr_initial/source/author/`. |
| BBR's modified TFHE and concrete-csprng | BSD 3-Clause Clear licenses retained in `experiments/bbr/source/tfhe-rs-odd/` and its component directories. |
| Refined-LHE | MIT, copyright KAIST-CryptLab; each `source/refined-tfhe-lhe/LICENSE` is retained. |
| Meta-PBS | Apache License 2.0; each `source/META-FBS/LICENSE` is retained. |
| TFHE-rs library evidence | Upstream license accompanies copied excerpts in `docs/correctness/library_evidence/`. Cargo-fetched TFHE-rs and other dependencies retain their own licenses. |

Cargo.lock, go.mod/go.sum, author citations, and provenance records identify
other dependencies. Their source/build caches are not bundled. Historical
snapshots may contain duplicate license copies intentionally, so a snapshot
can be read with its original notices. No license is asserted over third-party
papers, citations, or external websites.
