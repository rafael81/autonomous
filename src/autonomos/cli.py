"""CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from .examples import build_examples_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autonomos",
        description="Capture and normalize Codex CLI observation traces.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Print tool version.")

    build_examples = subparsers.add_parser("build-examples", help="Generate the first 10 observation examples.")
    build_examples.add_argument(
        "--output-dir",
        default="examples",
        help="Directory where example datasets will be written.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "version":
        print("autonomos 0.1.0")
        return 0
    if args.command == "build-examples":
        build_examples_dataset(Path(args.output_dir))
        print(f"wrote examples to {args.output_dir}")
        return 0

    parser.print_help()
    return 0
