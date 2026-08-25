"""FASTA validation and aggregate QC summaries."""

from __future__ import annotations

import hashlib
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from .models import FastaRecord
from .parser import parse_fasta

Alphabet = Literal["auto", "dna", "rna", "protein"]

DNA_SYMBOLS = frozenset("ACGTRYSWKMBDHVN")
RNA_SYMBOLS = frozenset("ACGURYSWKMBDHVN")
PROTEIN_SYMBOLS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")
GAP_SYMBOLS = frozenset("-.")


def identifier_fingerprint(identifier: str) -> str:
    """Return a short non-reversible label suitable for validation logs."""

    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:12]


def infer_alphabet(records: list[FastaRecord]) -> Literal["dna", "rna", "protein"]:
    """Infer a conservative alphabet from a collection of records."""

    symbols = set().union(*(set(record.sequence.upper()) for record in records))
    symbols -= GAP_SYMBOLS | {"*"}
    if symbols <= DNA_SYMBOLS:
        return "dna"
    if symbols <= RNA_SYMBOLS and "U" in symbols:
        return "rna"
    return "protein"


def allowed_symbols(
    alphabet: Literal["dna", "rna", "protein"],
    *,
    allow_gaps: bool,
    allow_stop: bool,
) -> frozenset[str]:
    """Build the accepted symbol set for a validation policy."""

    base = {"dna": DNA_SYMBOLS, "rna": RNA_SYMBOLS, "protein": PROTEIN_SYMBOLS}[alphabet]
    accepted = set(base)
    if allow_gaps:
        accepted.update(GAP_SYMBOLS)
    if allow_stop:
        accepted.add("*")
    return frozenset(accepted)


def validate_records(
    records: list[FastaRecord],
    *,
    alphabet: Alphabet = "auto",
    allow_gaps: bool = False,
    allow_stop: bool = False,
) -> dict[str, Any]:
    """Validate records without emitting raw identifiers or sequence content."""

    selected_alphabet = infer_alphabet(records) if alphabet == "auto" else alphabet
    accepted = allowed_symbols(
        selected_alphabet,
        allow_gaps=allow_gaps,
        allow_stop=allow_stop,
    )
    seen: set[str] = set()
    issues: list[dict[str, Any]] = []

    for record in records:
        fingerprint = identifier_fingerprint(record.identifier)
        if record.identifier in seen:
            issues.append(
                {
                    "code": "duplicate_identifier",
                    "record": fingerprint,
                    "line": record.source_line,
                }
            )
        seen.add(record.identifier)

        if not record.sequence:
            issues.append(
                {"code": "empty_sequence", "record": fingerprint, "line": record.source_line}
            )
            continue

        invalid = sorted(set(record.sequence.upper()) - accepted)
        if invalid:
            issues.append(
                {
                    "code": "invalid_symbols",
                    "record": fingerprint,
                    "line": record.source_line,
                    "symbols": invalid,
                }
            )

    return {
        "valid": not issues,
        "alphabet": selected_alphabet,
        "record_count": len(records),
        "issue_count": len(issues),
        "issues": issues,
    }


def validate_fasta(
    path: str | Path,
    *,
    alphabet: Alphabet = "auto",
    allow_gaps: bool = False,
    allow_stop: bool = False,
) -> dict[str, Any]:
    """Parse and validate a FASTA file."""

    return validate_records(
        list(parse_fasta(path)),
        alphabet=alphabet,
        allow_gaps=allow_gaps,
        allow_stop=allow_stop,
    )


def summarize_fasta(path: str | Path) -> dict[str, Any]:
    """Return aggregate QC metrics without exposing record identifiers."""

    records = list(parse_fasta(path))
    lengths = [len(record.sequence) for record in records]
    identifier_counts = Counter(record.identifier for record in records)
    residue_count = sum(lengths)

    if not lengths:
        return {
            "record_count": 0,
            "residue_count": 0,
            "minimum_length": None,
            "maximum_length": None,
            "mean_length": None,
            "median_length": None,
            "n50": None,
            "duplicate_identifier_count": 0,
        }

    cumulative = 0
    n50 = 0
    for length in sorted(lengths, reverse=True):
        cumulative += length
        if cumulative >= residue_count / 2:
            n50 = length
            break

    return {
        "record_count": len(records),
        "residue_count": residue_count,
        "minimum_length": min(lengths),
        "maximum_length": max(lengths),
        "mean_length": round(statistics.fmean(lengths), 2),
        "median_length": statistics.median(lengths),
        "n50": n50,
        "duplicate_identifier_count": sum(
            count - 1 for count in identifier_counts.values() if count > 1
        ),
    }
