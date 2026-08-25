"""Command-line interface for the FASTA research toolkit."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .operations import filter_fasta, pseudonymize_fasta, split_fasta
from .parser import FastaFormatError
from .quality import summarize_fasta, validate_fasta


def _add_alphabet_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--alphabet", choices=("auto", "dna", "rna", "protein"), default="auto")
    parser.add_argument("--allow-gaps", action="store_true")
    parser.add_argument("--allow-stop", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fasta-toolkit",
        description="Privacy-conscious FASTA validation and preparation.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate structure and sequence symbols")
    validate.add_argument("input", type=Path)
    _add_alphabet_options(validate)
    validate.add_argument("--json", action="store_true", dest="as_json")

    summarize = subparsers.add_parser("summarize", help="print aggregate, identifier-free QC")
    summarize.add_argument("input", type=Path)
    summarize.add_argument("--json", action="store_true", dest="as_json")

    filter_parser = subparsers.add_parser("filter", help="normalize and filter records")
    filter_parser.add_argument("input", type=Path)
    filter_parser.add_argument("output", type=Path)
    filter_parser.add_argument("--min-length", type=int, default=1)
    filter_parser.add_argument("--max-length", type=int)
    _add_alphabet_options(filter_parser)
    filter_parser.add_argument("--drop-invalid", action="store_true")
    filter_parser.add_argument("--strip-gaps", action="store_true")
    filter_parser.add_argument("--drop-descriptions", action="store_true")

    pseudonymize = subparsers.add_parser(
        "pseudonymize",
        help="replace identifiers with deterministic keyed hashes",
    )
    pseudonymize.add_argument("input", type=Path)
    pseudonymize.add_argument("output", type=Path)
    pseudonymize.add_argument("--key-env", default="FASTA_ID_KEY")
    pseudonymize.add_argument("--prefix", default="seq")
    pseudonymize.add_argument("--keep-descriptions", action="store_true")
    pseudonymize.add_argument("--mapping-output", type=Path)

    split_parser = subparsers.add_parser(
        "split",
        help="split FASTA records using a CSV assignment table",
    )
    split_parser.add_argument("input", type=Path)
    split_parser.add_argument("assignments", type=Path)
    split_parser.add_argument("output_directory", type=Path)
    split_parser.add_argument("--id-column", default="record_id")
    split_parser.add_argument("--group-column", default="group")
    split_parser.add_argument("--unassigned", choices=("error", "skip"), default="error")
    split_parser.add_argument("--force", action="store_true")
    return parser


def _print_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    for key, value in result.items():
        if key != "issues":
            print(f"{key}: {value}")
    for issue in result.get("issues", []):
        print(f"issue: {json.dumps(issue, sort_keys=True)}")


def run(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)

    if args.command == "validate":
        result = validate_fasta(
            args.input,
            alphabet=args.alphabet,
            allow_gaps=args.allow_gaps,
            allow_stop=args.allow_stop,
        )
        _print_result(result, as_json=args.as_json)
        return 0 if result["valid"] else 1

    if args.command == "summarize":
        _print_result(summarize_fasta(args.input), as_json=args.as_json)
        return 0

    if args.command == "filter":
        count = filter_fasta(
            args.input,
            args.output,
            minimum_length=args.min_length,
            maximum_length=args.max_length,
            alphabet=args.alphabet,
            allow_gaps=args.allow_gaps,
            allow_stop=args.allow_stop,
            drop_invalid=args.drop_invalid,
            strip_gaps=args.strip_gaps,
            drop_descriptions=args.drop_descriptions,
        )
        print(f"wrote_records: {count}")
        return 0

    if args.command == "pseudonymize":
        key = os.environ.get(args.key_env)
        if not key:
            raise ValueError(f"Required environment variable {args.key_env!r} is not set")
        count = pseudonymize_fasta(
            args.input,
            args.output,
            key=key,
            prefix=args.prefix,
            keep_descriptions=args.keep_descriptions,
            mapping_output=args.mapping_output,
        )
        print(f"wrote_records: {count}")
        return 0

    if args.command == "split":
        counts = split_fasta(
            args.input,
            args.assignments,
            args.output_directory,
            id_column=args.id_column,
            group_column=args.group_column,
            unassigned=args.unassigned,
            force=args.force,
        )
        print(json.dumps({"groups": len(counts), "records_by_group": counts}, indent=2))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


def main() -> None:
    try:
        raise SystemExit(run())
    except (FastaFormatError, FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
