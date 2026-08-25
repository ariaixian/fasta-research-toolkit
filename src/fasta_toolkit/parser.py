"""Streaming FASTA parsing and deterministic writing."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from .models import FastaRecord


class FastaFormatError(ValueError):
    """Raised when an input cannot be interpreted as FASTA."""


def parse_fasta(path: str | Path) -> Iterator[FastaRecord]:
    """Yield FASTA records from *path* without loading the full file into memory.

    Blank lines are ignored. Sequence lines may be wrapped, and horizontal
    whitespace inside a sequence line is removed. Semantic validation is kept
    separate so callers can choose DNA, RNA, or protein rules.
    """

    input_path = Path(path)
    identifier: str | None = None
    description = ""
    fragments: list[str] = []
    header_line: int | None = None

    with input_path.open("r", encoding="utf-8", newline=None) as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith(">"):
                if identifier is not None:
                    yield FastaRecord(
                        identifier=identifier,
                        description=description,
                        sequence="".join(fragments),
                        source_line=header_line,
                    )

                header = line[1:].strip()
                if not header:
                    raise FastaFormatError(f"Empty FASTA header at line {line_number}")
                parts = header.split(maxsplit=1)
                identifier = parts[0]
                description = parts[1] if len(parts) == 2 else ""
                fragments = []
                header_line = line_number
                continue

            if identifier is None:
                raise FastaFormatError(
                    f"Sequence content appears before the first header at line {line_number}"
                )
            fragments.append("".join(line.split()))

    if identifier is not None:
        yield FastaRecord(
            identifier=identifier,
            description=description,
            sequence="".join(fragments),
            source_line=header_line,
        )


@contextmanager
def atomic_text_writer(path: str | Path) -> Iterator[TextIO]:
    """Write a UTF-8 text file atomically in its destination directory."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            yield handle
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def write_fasta(
    records: Iterable[FastaRecord],
    path: str | Path,
    *,
    line_width: int = 80,
) -> int:
    """Write *records* deterministically and return the number written."""

    if line_width < 1:
        raise ValueError("line_width must be positive")

    count = 0
    with atomic_text_writer(path) as handle:
        for record in records:
            handle.write(f">{record.header}\n")
            for offset in range(0, len(record.sequence), line_width):
                handle.write(f"{record.sequence[offset : offset + line_width]}\n")
            count += 1
    return count
