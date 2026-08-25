# Reproducible workflow

This workflow separates reusable engineering from private scientific analysis.
Paths below are examples; keep actual research inputs and outputs outside the
repository.

## 1. Create a private run directory

```text
/secure/project-run/
├── raw/             # immutable source files
├── working/         # pseudonymized and filtered files
├── mappings/        # restricted identifier maps
├── assignments/     # reviewed human decisions
├── results/         # generated outputs
└── run-notes.md     # commands, checksums, versions, and decisions
```

Record source checksums before any transformation. Restrict access to `raw/` and
`mappings/`, and back them up according to the project's data-management plan.

## 2. Validate without exposing identifiers

```bash
fasta-toolkit validate /secure/project-run/raw/input.fasta \
  --alphabet protein --json > /secure/project-run/results/validation.json
```

The report contains aggregate counts, line numbers, issue codes, and one-way
identifier fingerprints. It does not print headers or sequences.

## 3. Pseudonymize early

```bash
export FASTA_ID_KEY="<retrieve from an approved secret store>"
fasta-toolkit pseudonymize \
  /secure/project-run/raw/input.fasta \
  /secure/project-run/working/pseudonymous.fasta \
  --mapping-output /secure/project-run/mappings/identifier-mapping.csv
```

Descriptions are removed by default because free text often contains sample or
study context. Use the same secret key when stable labels are required across runs.

## 4. Apply explicit QC policy

```bash
fasta-toolkit filter \
  /secure/project-run/working/pseudonymous.fasta \
  /secure/project-run/working/filtered.fasta \
  --alphabet protein \
  --min-length <documented-threshold> \
  --drop-invalid \
  --drop-descriptions
```

The threshold is deliberately not built into the software. Record its rationale in
the private run notes or protocol.

## 5. Capture manual decisions as data

When expert review is necessary, export only the minimum decision needed by the next
step. Use a CSV with pseudonymous identifiers:

```csv
record_id,group
seq_example001,group-a
seq_example002,group-b
```

Then create one FASTA file per group:

```bash
fasta-toolkit split \
  /secure/project-run/working/filtered.fasta \
  /secure/project-run/assignments/reviewed.csv \
  /secure/project-run/results/groups
```

This replaces ad hoc copying and renaming while keeping the scientific judgment
visible and reviewable. The assignment table remains private if its group labels or
membership reveal unpublished findings.

## 6. Align and construct a distance tree locally

Install the optional Python dependency and an approved local aligner. Then run:

```bash
fasta-toolkit align \
  /secure/project-run/working/filtered.fasta \
  /secure/project-run/results/aligned.fasta \
  --engine muscle5 \
  --threads 4

fasta-toolkit tree \
  /secure/project-run/results/aligned.fasta \
  /secure/project-run/results/tree.nwk \
  --model blosum62 \
  --distance-output /secure/project-run/results/distances.csv
```

Both steps run locally. Record the toolkit version, aligner name and version, distance
model, thread count, and input/output checksums in the private run notes. Tree and
matrix outputs remain private until cleared for publication.

## 7. Generate identifier-free QC

```bash
fasta-toolkit summarize /secure/project-run/working/filtered.fasta --json \
  > /secure/project-run/results/summary.json
```

Compare record counts between stages and record the exact toolkit version:

```bash
fasta-toolkit --version
```

## 8. Publication gate

Before committing any change:

```bash
python scripts/audit_public_tree.py .
git status --short
git diff --cached
```

The audit is a guardrail, not a substitute for human review or institutional data
policy. A second person should review any release derived from unpublished work.
