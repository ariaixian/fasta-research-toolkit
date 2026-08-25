import csv
from pathlib import Path

import pytest
from Bio import Phylo

from fasta_toolkit.phylogeny import build_neighbor_joining_tree


def _write_alignment(path: Path, records: list[tuple[str, str]]) -> None:
    path.write_text(
        "".join(f">{identifier}\n{sequence}\n" for identifier, sequence in records),
        encoding="utf-8",
    )


def test_build_neighbor_joining_tree_and_distance_matrix(tmp_path: Path) -> None:
    alignment = tmp_path / "aligned.fasta"
    _write_alignment(
        alignment,
        [
            ("synthetic_a", "ACDEFGHIKLMNPQRSTVWY"),
            ("synthetic_b", "ACDEYGHIKLMNPQRSTVWY"),
            ("synthetic_c", "ACDEFGHIKLMNPQKSTVWY"),
        ],
    )
    tree_path = tmp_path / "tree.nwk"
    distance_path = tmp_path / "distances.csv"

    result = build_neighbor_joining_tree(
        alignment,
        tree_path,
        model="blosum62",
        distance_output=distance_path,
        midpoint_root=True,
    )

    assert result == {
        "method": "neighbor-joining",
        "distance_model": "blosum62",
        "record_count": 3,
        "midpoint_rooted": True,
        "output": str(tree_path),
    }
    tree = Phylo.read(tree_path, "newick")
    assert sorted(terminal.name for terminal in tree.get_terminals()) == [
        "synthetic_a",
        "synthetic_b",
        "synthetic_c",
    ]
    with distance_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["record_id", "synthetic_a", "synthetic_b", "synthetic_c"]
    assert len(rows) == 4


def test_tree_requires_input_and_three_unique_records(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        build_neighbor_joining_tree(tmp_path / "missing.fasta", tmp_path / "tree.nwk")

    too_small = tmp_path / "small.fasta"
    _write_alignment(too_small, [("a", "ACDE"), ("b", "ACDF")])
    with pytest.raises(ValueError, match="at least three"):
        build_neighbor_joining_tree(too_small, tmp_path / "tree.nwk", model="identity")

    duplicate = tmp_path / "duplicate.fasta"
    _write_alignment(
        duplicate,
        [("same", "ACDE"), ("same", "ACDF"), ("third", "ACDG")],
    )
    with pytest.raises(ValueError, match="unique"):
        build_neighbor_joining_tree(duplicate, tmp_path / "tree.nwk", model="identity")
