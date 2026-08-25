# Privacy and pre-publication safety

FASTA headers, file names, metadata tables, notebook outputs, and directory paths can
reveal more than the sequence body itself. This project therefore treats the entire
research context as sensitive until explicitly cleared for release.

## Threat model

The safeguards are designed to reduce accidental disclosure through:

- raw or derived sequence files committed to Git;
- sample names embedded in FASTA descriptions;
- absolute paths that expose people, organizations, or project names;
- identifier maps and secret keys;
- notebook cell outputs and execution history;
- figures, alignments, trees, reports, and office-document metadata;
- third-party web services that receive unpublished inputs.
- tree or distance outputs that preserve sensitive record identifiers.

## Required controls

### Keep research data out of the repository

Store raw data, derived data, mapping tables, and results in an access-controlled
location. The `.gitignore` is intentionally broad. Do not weaken it merely to make a
local command more convenient.

### Pseudonymize, then minimize

Run `pseudonymize` before downstream transformations. Headers are replaced with a
keyed digest, and descriptions are dropped by default. A keyed digest is preferable
to a plain hash when identifiers are guessable.

Pseudonymization is not anonymization. Anyone with the key or mapping can reconnect
records to their original identifiers. Store both separately from the public code.

### Avoid sensitive logs

Validation issues identify records using one-way fingerprints. Aggregate summaries
do not include IDs or sequence content. Redirect private run logs to the secure run
directory, never to this repository.

### Review external services

Do not upload unpublished inputs to remote alignment, search, visualization, AI, or
notebook services without confirming authorization, retention, and confidentiality
terms. Prefer approved local tooling for sensitive material.

The `align` and `tree` commands in this repository run locally. Their output can still
contain identifying headers, so pseudonymize first and keep generated files outside
Git.

## Release checklist

- [ ] Only source code, documentation, and visibly synthetic fixtures are tracked.
- [ ] No source or derived sequence data is present.
- [ ] No real identifiers, metadata fields, study labels, or group names are present.
- [ ] No names, email addresses, institutions, locations, or absolute local paths are present.
- [ ] No notebooks, reports, office documents, figures, trees, alignments, or archives are present.
- [ ] No API keys, tokens, private keys, identifier maps, or environment files are present.
- [ ] `python scripts/audit_public_tree.py .` passes.
- [ ] Tests and static checks pass from a clean checkout.
- [ ] A human reviewer has inspected every tracked file and the complete Git history.

## Reporting a security issue

Do not open a public issue if a disclosure is discovered. Follow the private reporting
process in [SECURITY.md](../SECURITY.md).
