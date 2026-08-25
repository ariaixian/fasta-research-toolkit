from pathlib import Path

import pytest

from fasta_toolkit.alignment import (
    AlignmentError,
    build_alignment_command,
    default_executable,
    run_alignment,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_muscle5_command() -> None:
    command = build_alignment_command(
        engine="muscle5",
        executable="muscle",
        input_path="input.fasta",
        output_path="output.fasta",
        threads=4,
    )

    assert command == [
        "muscle",
        "-align",
        "input.fasta",
        "-output",
        "output.fasta",
        "-threads",
        "4",
    ]


def test_build_legacy_and_clustal_commands() -> None:
    assert (
        build_alignment_command(
            engine="muscle3",
            executable="muscle",
            input_path="input.fasta",
            output_path="output.aln",
            output_format="clustal",
        )[-1]
        == "-clwstrict"
    )
    assert build_alignment_command(
        engine="clustalw",
        executable="clustalw2",
        input_path="input.fasta",
        output_path="output.aln",
        output_format="clustal",
        sequence_type="dna",
    ) == [
        "clustalw2",
        "-INFILE=input.fasta",
        "-OUTFILE=output.aln",
        "-OUTPUT=CLUSTAL",
        "-TYPE=DNA",
        "-QUIET",
    ]


def test_alignment_command_validates_options() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_alignment_command(
            engine="muscle5",
            executable="muscle",
            input_path="input.fasta",
            output_path="output.fasta",
            threads=0,
        )
    with pytest.raises(ValueError, match="MUSCLE 5"):
        build_alignment_command(
            engine="muscle5",
            executable="muscle",
            input_path="input.fasta",
            output_path="output.aln",
            output_format="clustal",
        )


def _write_fake_muscle(path: Path, *, produces_output: bool = True, status: int = 0) -> None:
    output_action = (
        "shutil.copyfile(args[args.index('-align') + 1], args[args.index('-output') + 1])"
        if produces_output
        else "pass"
    )
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import shutil\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        f"{output_action}\n"
        f"raise SystemExit({status})\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_run_alignment_uses_local_executable_and_atomic_output(tmp_path: Path) -> None:
    executable = tmp_path / "fake-muscle"
    _write_fake_muscle(executable)
    output = tmp_path / "aligned.fasta"

    result = run_alignment(
        FIXTURES / "valid_protein.fasta",
        output,
        executable=str(executable),
        threads=2,
    )

    assert result["engine"] == "muscle5"
    assert result["threads"] == 2
    assert output.read_text(encoding="utf-8") == (FIXTURES / "valid_protein.fasta").read_text(
        encoding="utf-8"
    )


def test_run_alignment_reports_safe_failures(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        run_alignment(tmp_path / "missing.fasta", tmp_path / "output.fasta")
    with pytest.raises(AlignmentError, match="not installed"):
        run_alignment(
            FIXTURES / "valid_protein.fasta",
            tmp_path / "output.fasta",
            executable="definitely-not-an-installed-aligner",
        )

    failing = tmp_path / "failing-muscle"
    _write_fake_muscle(failing, status=7)
    with pytest.raises(AlignmentError, match="exit status 7"):
        run_alignment(
            FIXTURES / "valid_protein.fasta",
            tmp_path / "output.fasta",
            executable=str(failing),
        )

    silent = tmp_path / "silent-muscle"
    _write_fake_muscle(silent, produces_output=False)
    with pytest.raises(AlignmentError, match="non-empty output"):
        run_alignment(
            FIXTURES / "valid_protein.fasta",
            tmp_path / "output.fasta",
            executable=str(silent),
        )


def test_default_executables() -> None:
    assert default_executable("muscle5") == "muscle"
    assert default_executable("clustalw") == "clustalw2"
