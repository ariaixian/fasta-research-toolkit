from pathlib import Path

from fasta_toolkit.models import FastaRecord
from fasta_toolkit.quality import (
    identifier_fingerprint,
    infer_alphabet,
    summarize_fasta,
    validate_fasta,
    validate_records,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_valid_protein() -> None:
    report = validate_fasta(FIXTURES / "valid_protein.fasta", alphabet="protein")

    assert report == {
        "valid": True,
        "alphabet": "protein",
        "record_count": 2,
        "issue_count": 0,
        "issues": [],
    }


def test_validate_redacts_identifiers_and_reports_symbols() -> None:
    report = validate_fasta(FIXTURES / "invalid_protein.fasta", alphabet="protein")

    assert report["valid"] is False
    assert [issue["code"] for issue in report["issues"]] == [
        "duplicate_identifier",
        "invalid_symbols",
    ]
    assert all(
        issue["record"] == identifier_fingerprint("record_one") for issue in report["issues"]
    )
    assert "record_one" not in str(report)
    assert report["issues"][1]["symbols"] == ["!"]


def test_summarize_is_identifier_free() -> None:
    summary = summarize_fasta(FIXTURES / "valid_protein.fasta")

    assert summary == {
        "record_count": 2,
        "residue_count": 40,
        "minimum_length": 20,
        "maximum_length": 20,
        "mean_length": 20.0,
        "median_length": 20.0,
        "n50": 20,
        "duplicate_identifier_count": 0,
    }
    assert "record_one" not in str(summary)


def test_summarize_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.fasta"
    empty.write_text("", encoding="utf-8")

    assert summarize_fasta(empty)["record_count"] == 0
    assert summarize_fasta(empty)["n50"] is None


def test_infer_alphabets() -> None:
    assert infer_alphabet([FastaRecord("dna", "", "ACGTN")]) == "dna"
    assert infer_alphabet([FastaRecord("rna", "", "ACGUN")]) == "rna"
    assert infer_alphabet([FastaRecord("protein", "", "MELK")]) == "protein"


def test_validation_policy_controls_gaps_stops_and_empty_records() -> None:
    records = [
        FastaRecord("gapped", "", "ACD-*", source_line=1),
        FastaRecord("empty", "", "", source_line=3),
    ]

    report = validate_records(
        records,
        alphabet="protein",
        allow_gaps=True,
        allow_stop=True,
    )

    assert report["valid"] is False
    assert report["issues"] == [
        {
            "code": "empty_sequence",
            "record": identifier_fingerprint("empty"),
            "line": 3,
        }
    ]
