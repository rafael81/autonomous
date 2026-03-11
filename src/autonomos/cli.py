"""CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from .codex_exec import build_exec_command, render_codex_config_toml
from .compare import compare_normalized_sequences
from .config import load_ws_auth_config
from .examples import build_examples_dataset
from .io import read_jsonl
from .live_capture import run_capture


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

    print_ws = subparsers.add_parser("print-ws-config", help="Print Codex config TOML for websocket-based capture.")
    print_ws.add_argument("--output", help="Optional output path for config.toml")

    capture_live = subparsers.add_parser("capture-live", help="Run codex exec and capture stdout/stderr.")
    capture_live.add_argument("prompt", help="Prompt to send to codex exec.")
    capture_live.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    capture_live.add_argument("--cwd", default=".", help="Working directory for codex exec.")

    compare = subparsers.add_parser("compare", help="Compare two normalized JSONL traces structurally.")
    compare.add_argument("expected", help="Expected normalized.jsonl path.")
    compare.add_argument("actual", help="Actual normalized.jsonl path.")
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
    if args.command == "print-ws-config":
        config_text = render_codex_config_toml(load_ws_auth_config())
        if args.output:
            Path(args.output).write_text(config_text, encoding="utf-8")
        print(config_text, end="" if config_text.endswith("\n") else "\n")
        return 0
    if args.command == "capture-live":
        command = build_exec_command(prompt=args.prompt, profile=args.profile, cwd=Path(args.cwd))
        result = run_capture(command, cwd=Path(args.cwd))
        print(f"command={' '.join(result.command)}")
        print(f"returncode={result.returncode}")
        if result.stdout:
            print("stdout:")
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print("stderr:")
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
        return result.returncode
    if args.command == "compare":
        result = compare_normalized_sequences(read_jsonl(Path(args.expected)), read_jsonl(Path(args.actual)))
        print(result.summary)
        for detail in result.details:
            print(detail)
        return 0 if result.matches else 1

    parser.print_help()
    return 0
