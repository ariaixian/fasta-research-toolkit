import csv
from pathlib import Path

import pytest

from fasta_toolkit.models import FastaRecord
from fasta_toolkit.operations import (
    filter_records,
    pseudonymize_fasta,
    pseudonymize_records,
    read_assignments,
    split_fasta,
)
from fasta_toolkit.parser import parse_fasta

FIXTURES = Path(__file__).parent / "fixtures"


def test_filter_records_normalizes_and_applies_policy() -> None:
    records = [
        FastaRecord("short", "private description", "acde"),
        FastaRecord("keep", "private description", "acdefghikl"),
        FastaRecord("invalid", "", "ACD!EFGHIKL"),
    ]

    filtered = filter_records(
        records,
        minimum_length=8,
        alphabet="protein",
        drop_invalid=True,
        drop_descriptions=True,
    )

    assert filtered == [FastaRecord("keep", "", "ACDEFGHIKL")]


def test_filter_records_rejects_invalid_by_default() -> None:
    with pytest.raises(ValueError, match="invalid symbols"):
        filter_records([FastaRecord("bad", "", "ACD!")], alphabet="protein")


def test_filter_records_validates_range_and_can_strip_gaps() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        filter_records([], minimum_length=-1)
    with pytest.raises(ValueError, match="smaller"):
        filter_records([], minimum_length=10, maximum_length=5)

    filtered = filter_records(
        [FastaRecord("gapped", "", "ACD-EF")],
        alphabet="protein",
        strip_gaps=True,
    )
    assert filtered[0].sequence == "ACDEF"


def test_pseudonymization_is_deterministic_and_drops_descriptions() -> None:
    source = [FastaRecord("private-id", "sensitive context", "ACDE")]

    first, mapping = pseudonymize_records(source, key="test-only-secret", prefix="sample")
    second, _ = pseudonymize_records(source, key="test-only-secret", prefix="sample")

    assert first == second
    assert first[0].identifier.startswith("sample_")
    assert first[0].identifier != "private-id"
    assert first[0].description == ""
    assert mapping == [("private-id", first[0].identifier)]


def test_pseudonymization_validates_key_and_prefix() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        pseudonymize_records([], key="")
    with pytest.raises(ValueError, match="prefix"):
        pseudonymize_records([], key="secret", prefix="1-invalid")


def test_pseudonymize_fasta_writes_optional_private_mapping(tmp_path: Path) -> None:
    output = tmp_path / "pseudonymous.fasta"
    mapping_path = tmp_path / "identifier-mapping.csv"

    count = pseudonymize_fasta(
        FIXTURES / "valid_protein.fasta",
        output,
        key="test-only-secret",
        mapping_output=mapping_path,
    )

    assert count == 2
    assert all(record.description == "" for record in parse_fasta(output))
    with mapping_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["original_id"] == "record_one"


def test_split_fasta_uses_safe_group_filenames(tmp_path: Path) -> None:
    output_directory = tmp_path / "groups"

    counts = split_fasta(
        FIXTURES / "valid_protein.fasta",
        FIXTURES / "assignments.csv",
        output_directory,
    )

    assert counts == {"Group A": 1, "Group B": 1}
    assert [record.identifier for record in parse_fasta(output_directory / "group-a.fasta")] == [
        "record_one"
    ]


def test_split_refuses_to_overwrite(tmp_path: Path) -> None:
    output_directory = tmp_path / "groups"
    split_fasta(
        FIXTURES / "valid_protein.fasta",
        FIXTURES / "assignments.csv",
        output_directory,
    )

    with pytest.raises(FileExistsError, match="Refusing"):
        split_fasta(
            FIXTURES / "valid_protein.fasta",
            FIXTURES / "assignments.csv",
            output_directory,
        )


def test_split_can_skip_unassigned_and_force_overwrite(tmp_path: Path) -> None:
    assignments = tmp_path / "partial.csv"
    assignments.write_text("record_id,group\nrecord_one,Only Group\n", encoding="utf-8")
    output_directory = tmp_path / "groups"

    counts = split_fasta(
        FIXTURES / "valid_protein.fasta",
        assignments,
        output_directory,
        unassigned="skip",
    )
    assert counts == {"Only Group": 1}
    assert split_fasta(
        FIXTURES / "valid_protein.fasta",
        assignments,
        output_directory,
        unassigned="skip",
        force=True,
    ) == {"Only Group": 1}


def test_assignment_table_requires_expected_columns(tmp_path: Path) -> None:
    assignments = tmp_path / "bad.csv"
    assignments.write_text("wrong,columns\na,b\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain"):
        read_assignments(assignments)
