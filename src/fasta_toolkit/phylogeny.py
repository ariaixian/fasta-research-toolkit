"""Distance-matrix and Neighbor-Joining tree construction."""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from typing import Literal

from .parser import atomic_text_writer

AlignmentInputFormat = Literal["fasta", "clustal"]
DistanceModel = Literal["identity", "blosum62"]


class AnalysisDependencyError(RuntimeError):
    """Raised when optional local analysis dependencies are unavailable."""


def _biopython_components():  # type: ignore[no-untyped-def]
    try:
        from Bio import AlignIO, Phylo
        from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
    except ImportError as error:
        raise AnalysisDependencyError(
            "Tree construction requires the optional analysis dependencies; "
            "install with 'pip install fasta-research-toolkit[analysis]'"
        ) from error
    return AlignIO, Phylo, DistanceCalculator, DistanceTreeConstructor


def write_distance_matrix(distance_matrix, path: str | Path) -> None:  # type: ignore[no-untyped-def]
    """Write a complete symmetric distance matrix as CSV."""

    with atomic_text_writer(path) as handle:
        writer = csv.writer(handle)
        writer.writerow(["record_id", *distance_matrix.names])
        for row_name in distance_matrix.names:
            writer.writerow(
                [row_name, *(distance_matrix[row_name, column] for column in distance_matrix.names)]
            )


def build_neighbor_joining_tree(
    alignment_path: str | Path,
    output_path: str | Path,
    *,
    alignment_format: AlignmentInputFormat = "fasta",
    model: DistanceModel = "blosum62",
    distance_output: str | Path | None = None,
    midpoint_root: bool = False,
) -> dict[str, str | int | bool]:
    """Build a deterministic local Neighbor-Joining tree in Newick format."""

    AlignIO, Phylo, DistanceCalculator, DistanceTreeConstructor = _biopython_components()
    source = Path(alignment_path)
    destination = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Alignment does not exist: {source}")

    alignment = AlignIO.read(str(source), alignment_format)
    if len(alignment) < 3:
        raise ValueError("Neighbor-Joining requires at least three aligned records")
    if len({record.id for record in alignment}) != len(alignment):
        raise ValueError("Aligned record identifiers must be unique")

    calculator = DistanceCalculator(model)
    distance_matrix = calculator.get_distance(alignment)
    tree = DistanceTreeConstructor().nj(distance_matrix)
    if midpoint_root:
        tree.root_at_midpoint()
    if distance_output is not None:
        write_distance_matrix(distance_matrix, distance_output)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.name}.tree-",
    ) as temporary_directory:
        temporary_output = Path(temporary_directory) / "tree.nwk"
        Phylo.write(tree, str(temporary_output), "newick")
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise RuntimeError("Tree construction completed without a non-empty output")
        os.replace(temporary_output, destination)

    return {
        "method": "neighbor-joining",
        "distance_model": model,
        "record_count": len(alignment),
        "midpoint_rooted": midpoint_root,
        "output": str(destination),
    }
