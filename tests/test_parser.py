from pathlib import Path

import pytest

from fasta_toolkit.models import FastaRecord
from fasta_toolkit.parser import FastaFormatError, parse_fasta, write_fasta

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_fasta_preserves_identifier_description_and_sequence() -> None:
    records = list(parse_fasta(FIXTURES / "valid_protein.fasta"))

    assert records == [
        FastaRecord("record_one", "synthetic fixture", "ACDEFGHIKLMNPQRSTVWY", 1),
        FastaRecord("record_two", "", "MNPQRSTVWYACDEFGHIKL", 3),
    ]


def test_parse_fasta_rejects_content_before_header(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.fasta"
    invalid.write_text("ACGT\n>later\nACGT\n", encoding="utf-8")

    with pytest.raises(FastaFormatError, match="before the first header"):
        list(parse_fasta(invalid))


def test_write_fasta_wraps_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "output.fasta"
    records = [FastaRecord("synthetic", "fixture", "ACDEFGHIKL")]

    assert write_fasta(records, output, line_width=4) == 1
    assert output.read_text(encoding="utf-8") == ">synthetic fixture\nACDE\nFGHI\nKL\n"
    assert next(parse_fasta(output)).sequence == "ACDEFGHIKL"


def test_write_fasta_rejects_non_positive_width(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        write_fasta([], tmp_path / "output.fasta", line_width=0)
