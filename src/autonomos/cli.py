"""CLI entrypoint."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autonomos",
        description="Capture and normalize Codex CLI observation traces.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Print tool version.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "version":
        print("autonomos 0.1.0")
        return 0

    parser.print_help()
    return 0
