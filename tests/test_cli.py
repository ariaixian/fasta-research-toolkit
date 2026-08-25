import json
from pathlib import Path

from fasta_toolkit.cli import run

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_cli_exit_status_and_json(capsys) -> None:  # type: ignore[no-untyped-def]
    status = run(
        [
            "validate",
            str(FIXTURES / "valid_protein.fasta"),
            "--alphabet",
            "protein",
            "--json",
        ]
    )

    assert status == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_filter_cli(tmp_path: Path) -> None:
    output = tmp_path / "filtered.fasta"

    status = run(
        [
            "filter",
            str(FIXTURES / "valid_protein.fasta"),
            str(output),
            "--alphabet",
            "protein",
            "--min-length",
            "20",
        ]
    )

    assert status == 0
    assert output.exists()


def test_summarize_pseudonymize_and_split_cli(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:  # type: ignore[no-untyped-def]
    source = FIXTURES / "valid_protein.fasta"
    pseudonymous = tmp_path / "pseudonymous.fasta"
    monkeypatch.setenv("TEST_FASTA_KEY", "test-only-secret")

    assert run(["summarize", str(source), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["record_count"] == 2
    assert (
        run(
            [
                "pseudonymize",
                str(source),
                str(pseudonymous),
                "--key-env",
                "TEST_FASTA_KEY",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assignments = tmp_path / "assignments.csv"
    lines = ["record_id,group"]
    for index, line in enumerate(pseudonymous.read_text(encoding="utf-8").splitlines()):
        if line.startswith(">"):
            lines.append(f"{line[1:]},group-{index}")
    assignments.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert run(["split", str(pseudonymous), str(assignments), str(tmp_path / "groups")]) == 0
    assert json.loads(capsys.readouterr().out)["groups"] == 2


def test_tree_cli(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    alignment = tmp_path / "aligned.fasta"
    alignment.write_text(
        ">synthetic_a\nACDEFGHIKL\n>synthetic_b\nACDEYGHIKL\n>synthetic_c\nACDEFGHIKM\n",
        encoding="utf-8",
    )
    output = tmp_path / "tree.nwk"

    assert run(["tree", str(alignment), str(output), "--model", "identity"]) == 0
    assert json.loads(capsys.readouterr().out)["method"] == "neighbor-joining"
    assert output.exists()
