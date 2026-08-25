"""Composable FASTA preparation operations."""

from __future__ import annotations

import csv
import hashlib
import hmac
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .models import FastaRecord
from .parser import atomic_text_writer, parse_fasta, write_fasta
from .quality import Alphabet, allowed_symbols, infer_alphabet


def filter_records(
    records: Iterable[FastaRecord],
    *,
    minimum_length: int = 1,
    maximum_length: int | None = None,
    alphabet: Alphabet = "auto",
    allow_gaps: bool = False,
    allow_stop: bool = False,
    drop_invalid: bool = False,
    strip_gaps: bool = False,
    drop_descriptions: bool = False,
) -> list[FastaRecord]:
    """Normalize and filter FASTA records according to explicit policy."""

    if minimum_length < 0:
        raise ValueError("minimum_length cannot be negative")
    if maximum_length is not None and maximum_length < minimum_length:
        raise ValueError("maximum_length cannot be smaller than minimum_length")

    materialized = list(records)
    selected_alphabet = infer_alphabet(materialized) if alphabet == "auto" else alphabet
    accepted = allowed_symbols(
        selected_alphabet,
        allow_gaps=allow_gaps,
        allow_stop=allow_stop,
    )
    output: list[FastaRecord] = []

    for record in materialized:
        sequence = record.sequence.upper()
        if strip_gaps:
            sequence = sequence.replace("-", "").replace(".", "")
        invalid = set(sequence) - accepted
        if invalid:
            if drop_invalid:
                continue
            symbols = "".join(sorted(invalid))
            raise ValueError(
                f"Record at line {record.source_line or '?'} contains invalid symbols: {symbols}"
            )
        if len(sequence) < minimum_length:
            continue
        if maximum_length is not None and len(sequence) > maximum_length:
            continue
        output.append(
            FastaRecord(
                identifier=record.identifier,
                description="" if drop_descriptions else record.description,
                sequence=sequence,
                source_line=record.source_line,
            )
        )
    return output


def filter_fasta(input_path: str | Path, output_path: str | Path, **kwargs: object) -> int:
    """Filter *input_path* and atomically write *output_path*."""

    records = filter_records(parse_fasta(input_path), **kwargs)
    return write_fasta(records, output_path)


def pseudonymize_records(
    records: Iterable[FastaRecord],
    *,
    key: str,
    prefix: str = "seq",
    keep_descriptions: bool = False,
) -> tuple[list[FastaRecord], list[tuple[str, str]]]:
    """Replace identifiers with deterministic keyed hashes.

    This is pseudonymization, not anonymization. The secret key and any mapping
    file must remain outside version control.
    """

    if not key:
        raise ValueError("A non-empty pseudonymization key is required")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", prefix):
        raise ValueError("prefix must start with a letter and contain only letters, digits, _ or -")

    output: list[FastaRecord] = []
    mapping: list[tuple[str, str]] = []
    pseudonyms: set[str] = set()
    key_bytes = key.encode("utf-8")

    for record in records:
        digest = hmac.new(key_bytes, record.identifier.encode("utf-8"), hashlib.sha256).hexdigest()
        pseudonym = f"{prefix}_{digest[:16]}"
        if pseudonym in pseudonyms:
            raise ValueError("Pseudonym collision detected; stop and use a different key")
        pseudonyms.add(pseudonym)
        mapping.append((record.identifier, pseudonym))
        output.append(
            FastaRecord(
                identifier=pseudonym,
                description=record.description if keep_descriptions else "",
                sequence=record.sequence,
                source_line=record.source_line,
            )
        )
    return output, mapping


def write_mapping(mapping: list[tuple[str, str]], path: str | Path) -> None:
    """Write a sensitive identifier map; callers must keep it out of Git."""

    with atomic_text_writer(path) as handle:
        writer = csv.writer(handle)
        writer.writerow(["original_id", "pseudonym"])
        writer.writerows(mapping)


def pseudonymize_fasta(
    input_path: str | Path,
    output_path: str | Path,
    *,
    key: str,
    prefix: str = "seq",
    keep_descriptions: bool = False,
    mapping_output: str | Path | None = None,
) -> int:
    """Pseudonymize a FASTA file and optionally write a private mapping."""

    records, mapping = pseudonymize_records(
        parse_fasta(input_path),
        key=key,
        prefix=prefix,
        keep_descriptions=keep_descriptions,
    )
    count = write_fasta(records, output_path)
    if mapping_output is not None:
        write_mapping(mapping, mapping_output)
    return count


def _safe_group_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("Group values must contain at least one letter or digit")
    return slug


def read_assignments(
    path: str | Path,
    *,
    id_column: str = "record_id",
    group_column: str = "group",
) -> dict[str, str]:
    """Read a two-column CSV assignment table with duplicate checks."""

    assignments: dict[str, str] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {id_column, group_column} <= set(reader.fieldnames):
            raise ValueError(f"Assignment CSV must contain {id_column!r} and {group_column!r}")
        for row_number, row in enumerate(reader, start=2):
            identifier = (row.get(id_column) or "").strip()
            group = (row.get(group_column) or "").strip()
            if not identifier or not group:
                raise ValueError(f"Blank identifier or group at assignment row {row_number}")
            if identifier in assignments and assignments[identifier] != group:
                raise ValueError(f"Conflicting assignment at row {row_number}")
            assignments[identifier] = group
    return assignments


def split_fasta(
    input_path: str | Path,
    assignments_path: str | Path,
    output_directory: str | Path,
    *,
    id_column: str = "record_id",
    group_column: str = "group",
    unassigned: str = "error",
    force: bool = False,
) -> dict[str, int]:
    """Split records into FASTA files using an auditable CSV assignment table."""

    if unassigned not in {"error", "skip"}:
        raise ValueError("unassigned must be 'error' or 'skip'")

    assignments = read_assignments(
        assignments_path,
        id_column=id_column,
        group_column=group_column,
    )
    grouped: dict[str, list[FastaRecord]] = defaultdict(list)
    for record in parse_fasta(input_path):
        group = assignments.get(record.identifier)
        if group is None:
            if unassigned == "skip":
                continue
            raise ValueError(f"A record at line {record.source_line or '?'} has no assignment")
        grouped[group].append(record)

    slug_owner: dict[str, str] = {}
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for group, records in sorted(grouped.items()):
        slug = _safe_group_slug(group)
        if slug in slug_owner and slug_owner[slug] != group:
            raise ValueError("Two group labels resolve to the same safe filename")
        slug_owner[slug] = group
        output_path = destination / f"{slug}.fasta"
        if output_path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite {output_path}")
        counts[group] = write_fasta(records, output_path)
    return counts
