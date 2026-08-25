# Local alignment and tree construction

This module preserves the general alignment and distance-tree engineering workflow
without encoding any dataset, research target, group label, or scientific conclusion.

## Supported aligners

The `align` command wraps an executable already installed on the machine:

| Engine | CLI option | Output | Conventional executable |
|---|---|---|---|
| MUSCLE 5 | `--engine muscle5` | FASTA | `muscle` |
| MUSCLE 3 | `--engine muscle3` | FASTA or Clustal | `muscle` |
| ClustalW 2 | `--engine clustalw` | FASTA or Clustal | `clustalw2` |

Use `--executable /approved/path/to/program` when the executable is not on `PATH`.
Arguments are passed as an argument vector; a shell is never invoked. The aligner
writes into a temporary directory, and the final file is moved into place only after
the command succeeds and produces a non-empty output.

```bash
fasta-toolkit align input.fasta aligned.fasta \
  --engine muscle5 \
  --threads 4 \
  --format fasta \
  --sequence-type protein
```

Record the external executable version in private run notes:

```bash
muscle -version
```

## Neighbor-Joining trees

Install the optional dependency and construct a tree from an existing alignment:

```bash
python -m pip install 'fasta-research-toolkit[analysis]'

fasta-toolkit tree aligned.fasta tree.nwk \
  --alignment-format fasta \
  --model blosum62 \
  --distance-output distances.csv \
  --midpoint-root
```

The command uses Biopython to calculate pairwise distances and construct a
Neighbor-Joining tree. Available distance policies are:

- `blosum62` for aligned protein sequences;
- `identity` for a simple fraction-of-mismatches distance.

At least three aligned records with unique identifiers are required. Newick and
distance-matrix outputs contain record identifiers, so pseudonymize the input before
alignment whenever headers are sensitive.

## Deliberate boundaries

The module does not perform remote database searches, choose an outgroup, assign
groups, calculate biological significance, or interpret a tree. Midpoint rooting is
optional and explicit. Bootstrap policy and model selection remain project-level
scientific decisions rather than hidden defaults.
