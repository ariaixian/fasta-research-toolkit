#!/usr/bin/env python3
"""Fail when a public repository contains common disclosure indicators.

This is a conservative guardrail, not a proof of anonymity. Project-specific terms
can be supplied at runtime through ``PUBLICATION_DENY_TERMS`` separated by ``||``.
The script never prints the configured terms or matching content.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_PUBLIC_FILE_BYTES = 500_000
ALLOWED_DATA_ROOTS = (Path("examples/synthetic"), Path("tests/fixtures"))
DATA_SUFFIXES = {".fa", ".fas", ".fna", ".faa", ".fasta", ".csv", ".tsv"}
BLOCKED_SUFFIXES = {
    ".aln",
    ".dnd",
    ".doc",
    ".docx",
    ".html",
    ".ipynb",
    ".meg",
    ".npy",
    ".npz",
    ".numbers",
    ".nwk",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rdata",
    ".rhistory",
    ".rds",
    ".tar",
    ".tgz",
    ".tree",
    ".xls",
    ".xlsx",
    ".zip",
}
IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}
IGNORED_NAMES = {".coverage", ".DS_Store"}


@dataclass(frozen=True)
class Finding:
    path: Path
    rule: str


def _is_under(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return [Path(part.decode("utf-8")) for part in result.stdout.split(b"\0") if part]
    return [
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in IGNORED_NAMES
        and not (set(path.relative_to(root).parts) & IGNORED_PARTS)
    ]


def _private_patterns() -> list[tuple[str, re.Pattern[str]]]:
    slash = "/"
    return [
        ("absolute-user-path", re.compile(slash + r"Users" + slash + r"[^/\s]+")),
        ("absolute-volume-path", re.compile(slash + r"Volumes" + slash + r"[^/\s]+")),
        ("absolute-home-path", re.compile(slash + r"home" + slash + r"[^/\s]+")),
        ("email-address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
        ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
        ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("private-key", re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ]


def _custom_terms() -> list[str]:
    raw = os.environ.get("PUBLICATION_DENY_TERMS", "")
    return [term.strip().casefold() for term in raw.split("||") if term.strip()]


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    terms = _custom_terms()
    patterns = _private_patterns()

    for relative in _tracked_files(root):
        path = root / relative
        if not path.is_file():
            continue
        suffix = path.suffix.casefold()
        relative_text = relative.as_posix().casefold()

        if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
            findings.append(Finding(relative, "file-too-large"))
        if suffix in BLOCKED_SUFFIXES:
            findings.append(Finding(relative, "blocked-file-type"))
        if suffix in DATA_SUFFIXES and not _is_under(relative, ALLOWED_DATA_ROOTS):
            findings.append(Finding(relative, "data-file-outside-reviewed-fixtures"))
        if any(term in relative_text for term in terms):
            findings.append(Finding(relative, "private-deny-term-in-path"))

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if suffix not in {".png", ".jpg", ".jpeg", ".gif"}:
                findings.append(Finding(relative, "unreviewed-binary-file"))
            continue

        for rule, pattern in patterns:
            if pattern.search(content):
                findings.append(Finding(relative, rule))
        content_casefold = content.casefold()
        if any(term in content_casefold for term in terms):
            findings.append(Finding(relative, "private-deny-term-in-content"))

        if not _is_under(relative, ALLOWED_DATA_ROOTS):
            for line in content.splitlines():
                if line.startswith(">"):
                    findings.append(Finding(relative, "fasta-header-outside-reviewed-fixtures"))
                    break
                compact = "".join(line.split()).upper()
                if len(compact) >= 120:
                    sequence_symbols = set("ACDEFGHIKLMNPQRSTVWYBXZJUO*-.")
                    ratio = sum(character in sequence_symbols for character in compact) / len(
                        compact
                    )
                    if ratio >= 0.95:
                        findings.append(Finding(relative, "sequence-like-content"))
                        break

    return sorted(set(findings), key=lambda finding: (finding.path.as_posix(), finding.rule))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    findings = audit(root)

    if findings:
        print(f"publication audit failed with {len(findings)} finding(s):", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.path.as_posix()}: {finding.rule}", file=sys.stderr)
        return 1

    print("publication audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
