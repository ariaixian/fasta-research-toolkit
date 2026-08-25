# FASTA Research Toolkit

[![CI](https://github.com/ariaixian/fasta-research-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/ariaixian/fasta-research-toolkit/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)

A small, tested command-line toolkit for preparing FASTA files in reproducible,
privacy-conscious research workflows. It turns fragile one-off file operations
into explicit commands with deterministic outputs and aggregate quality reports.

This repository contains software and fully synthetic fixtures only. It does not
contain source datasets, real sequence identifiers, metadata, scientific results,
figures, alignments, trees, reports, or unpublished research context.

## Capabilities

- Stream and write wrapped FASTA records with atomic output replacement.
- Validate DNA, RNA, or protein alphabets without printing raw identifiers.
- Report aggregate length and duplication metrics without exposing sequence content.
- Normalize case and filter records with explicit length and symbol policies.
- Pseudonymize identifiers with deterministic HMAC-SHA256 labels.
- Split records using an auditable CSV assignment table.
- Block common research-data formats from Git and audit the public tree before every push.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

fasta-toolkit validate examples/synthetic/proteins.fasta --alphabet protein
fasta-toolkit summarize examples/synthetic/proteins.fasta --json
fasta-toolkit filter examples/synthetic/proteins.fasta /tmp/filtered.fasta \
  --alphabet protein --min-length 20 --drop-descriptions
```

Pseudonymization requires a private key provided at runtime. The key and optional
mapping file must remain outside the repository.

```bash
export FASTA_ID_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
fasta-toolkit pseudonymize input.fasta /tmp/pseudonymous.fasta \
  --mapping-output /secure/location/identifier-mapping.csv
```

Split a pseudonymized file using an explicitly reviewed assignment table:

```bash
fasta-toolkit split examples/synthetic/proteins.fasta \
  examples/synthetic/assignments.csv /tmp/groups
```

See [the reproducible workflow](docs/workflow.md) for a staged research setup and
[the privacy guide](docs/privacy.md) before handling unpublished material.

## Design principles

1. **Raw data stays outside Git.** Data-like formats are ignored by default, with
   narrow exceptions for reviewed synthetic fixtures.
2. **Logs reveal structure, not identities.** Validation reports use short
   fingerprints instead of raw record identifiers.
3. **Every transformation is explicit.** Inputs, thresholds, and policies are
   command arguments that can be recorded in a private run manifest.
4. **Outputs are deterministic.** Stable ordering and wrapping make review and
   checksums meaningful.
5. **Manual decisions remain auditable.** Human classifications enter through a
   two-column assignment file rather than being hidden in notebook state.

## What this project intentionally does not do

The toolkit is not a complete scientific analysis pipeline. It does not encode a
study question, select a biological target, perform remote searches, infer trees,
or interpret results. Those choices belong in a private, versioned analysis layer
until the underlying research is ready for release.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest
python scripts/audit_public_tree.py .
```

Contributions must use synthetic fixtures and pass the publication audit. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE).
