"""Local multiple-sequence alignment wrappers.

The toolkit never uploads sequences. It executes a user-installed aligner as a
subprocess and atomically moves the completed alignment into place.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

AlignmentEngine = Literal["muscle5", "muscle3", "clustalw"]
AlignmentFormat = Literal["fasta", "clustal"]
SequenceType = Literal["protein", "dna"]


class AlignmentError(RuntimeError):
    """Raised when a local alignment process cannot complete safely."""


def default_executable(engine: AlignmentEngine) -> str:
    """Return the conventional executable name for an alignment engine."""

    return {"muscle5": "muscle", "muscle3": "muscle", "clustalw": "clustalw2"}[engine]


def build_alignment_command(
    *,
    engine: AlignmentEngine,
    executable: str,
    input_path: str | Path,
    output_path: str | Path,
    threads: int = 1,
    output_format: AlignmentFormat = "fasta",
    sequence_type: SequenceType = "protein",
) -> list[str]:
    """Build an argument-vector command without invoking a shell."""

    if threads < 1:
        raise ValueError("threads must be positive")
    input_text = str(Path(input_path))
    output_text = str(Path(output_path))

    if engine == "muscle5":
        if output_format != "fasta":
            raise ValueError("MUSCLE 5 output is handled as FASTA; choose --format fasta")
        return [
            executable,
            "-align",
            input_text,
            "-output",
            output_text,
            "-threads",
            str(threads),
        ]

    if engine == "muscle3":
        command = [executable, "-in", input_text, "-out", output_text]
        if output_format == "clustal":
            command.append("-clwstrict")
        return command

    if engine == "clustalw":
        clustal_format = "FASTA" if output_format == "fasta" else "CLUSTAL"
        clustal_type = "DNA" if sequence_type == "dna" else "PROTEIN"
        return [
            executable,
            f"-INFILE={input_text}",
            f"-OUTFILE={output_text}",
            f"-OUTPUT={clustal_format}",
            f"-TYPE={clustal_type}",
            "-QUIET",
        ]

    raise ValueError(f"Unsupported alignment engine: {engine}")


def _resolve_executable(executable: str) -> str:
    candidate = Path(executable)
    if candidate.parent != Path("."):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise AlignmentError("The configured alignment executable is unavailable")
    resolved = shutil.which(executable)
    if resolved is None:
        raise AlignmentError("The configured alignment executable is not installed")
    return resolved


def run_alignment(
    input_path: str | Path,
    output_path: str | Path,
    *,
    engine: AlignmentEngine = "muscle5",
    executable: str | None = None,
    threads: int = 1,
    output_format: AlignmentFormat = "fasta",
    sequence_type: SequenceType = "protein",
) -> dict[str, str | int]:
    """Run a local aligner and atomically publish its completed output."""

    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Input FASTA does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    resolved_executable = _resolve_executable(executable or default_executable(engine))

    with tempfile.TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.name}.alignment-",
    ) as temporary_directory:
        temporary_output = Path(temporary_directory) / f"alignment.{output_format}"
        command = build_alignment_command(
            engine=engine,
            executable=resolved_executable,
            input_path=source,
            output_path=temporary_output,
            threads=threads,
            output_format=output_format,
            sequence_type=sequence_type,
        )
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise AlignmentError(f"Alignment failed with exit status {completed.returncode}")
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise AlignmentError("Alignment process completed without a non-empty output")
        os.replace(temporary_output, destination)

    return {
        "engine": engine,
        "format": output_format,
        "threads": threads,
        "output": str(destination),
    }
