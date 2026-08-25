# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-25

### Added

- Local wrappers for MUSCLE 5, MUSCLE 3, and ClustalW 2.
- BLOSUM62 and identity distance-matrix calculation.
- Neighbor-Joining tree construction with optional midpoint rooting and Newick export.
- Alignment/tree documentation and automated tests using synthetic sequences.

## [0.1.0] - 2026-08-25

### Added

- Streaming FASTA parser and atomic writer.
- Identifier-free validation and aggregate QC summaries.
- Explicit length, alphabet, gap, stop-symbol, and description filtering.
- Deterministic HMAC-SHA256 identifier pseudonymization.
- CSV-driven record splitting with safe output names.
- Tests, CI, pre-commit checks, privacy documentation, and publication audit.

[Unreleased]: https://github.com/ariaixian/fasta-research-toolkit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ariaixian/fasta-research-toolkit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ariaixian/fasta-research-toolkit/releases/tag/v0.1.0
