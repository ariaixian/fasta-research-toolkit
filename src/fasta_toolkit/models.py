"""Core data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FastaRecord:
    """A single FASTA record.

    ``identifier`` is the first whitespace-delimited token in the header.
    ``description`` is the remainder of the header, without the leading ``>``.
    """

    identifier: str
    description: str
    sequence: str
    source_line: int | None = None

    @property
    def header(self) -> str:
        """Return the complete header text without ``>``."""

        return self.identifier if not self.description else f"{self.identifier} {self.description}"
