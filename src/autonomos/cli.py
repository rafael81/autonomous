"""CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from .baseline import compare_capture_against_baselines, promote_capture_to_example
from .codex_exec import build_exec_command, describe_ws_runtime, render_codex_config_toml
from .compare import compare_normalized_sequences
from .config import load_ws_auth_config
from .examples import build_examples_dataset
from .exec_normalizer import normalize_exec_events
from .io import read_jsonl
from .live_capture import run_capture, save_capture_session
from .workflow import observe_prompt


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
    print_ws.add_argument("--describe-runtime", action="store_true", help="Also print derived runtime websocket auth metadata.")

    capture_live = subparsers.add_parser("capture-live", help="Run codex exec and capture stdout/stderr.")
    capture_live.add_argument("prompt", help="Prompt to send to codex exec.")
    capture_live.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    capture_live.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    capture_live.add_argument("--output-dir", default="captures", help="Directory where live capture sessions will be stored.")

    compare = subparsers.add_parser("compare", help="Compare two normalized JSONL traces structurally.")
    compare.add_argument("expected", help="Expected normalized.jsonl path.")
    compare.add_argument("actual", help="Actual normalized.jsonl path.")

    normalize_exec = subparsers.add_parser("normalize-exec", help="Normalize codex exec JSONL into shared schema JSONL.")
    normalize_exec.add_argument("input", help="Path to raw codex exec JSONL.")
    normalize_exec.add_argument("output", help="Path to write normalized JSONL.")

    promote = subparsers.add_parser("promote-capture", help="Promote a saved capture session into example dataset format.")
    promote.add_argument("capture_dir", help="Capture session directory.")
    promote.add_argument("example_id", help="New example id.")
    promote.add_argument("--output-dir", default="examples_live", help="Directory where promoted examples are stored.")
    promote.add_argument("--prompt", help="Optional prompt override.")

    compare_baselines = subparsers.add_parser("compare-baselines", help="Compare a normalized capture against all baseline examples.")
    compare_baselines.add_argument("normalized", help="Path to normalized capture JSONL.")
    compare_baselines.add_argument("--baselines-dir", default="examples", help="Baseline examples directory.")

    observe = subparsers.add_parser("observe", help="Run the full observation pipeline: capture, normalize, promote, compare.")
    observe.add_argument("prompt", help="Prompt to send to codex exec.")
    observe.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    observe.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    observe.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    observe.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    observe.add_argument("--baselines-dir", default="examples", help="Baseline examples directory.")
    observe.add_argument("--example-id", help="Override promoted example id.")
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
        auth = load_ws_auth_config()
        config_text = render_codex_config_toml(auth)
        if args.output:
            Path(args.output).write_text(config_text, encoding="utf-8")
        print(config_text, end="" if config_text.endswith("\n") else "\n")
        if args.describe_runtime:
            print(describe_ws_runtime(auth))
        return 0
    if args.command == "capture-live":
        command = build_exec_command(prompt=args.prompt, profile=args.profile, cwd=Path(args.cwd))
        result = run_capture(command, cwd=Path(args.cwd))
        saved = save_capture_session(
            result=result,
            prompt=args.prompt,
            output_root=Path(args.output_dir),
        )
        print(f"command={' '.join(result.command)}")
        print(f"returncode={result.returncode}")
        print(f"session_dir={saved.session_dir}")
        if saved.raw_jsonl_path:
            print(f"raw_jsonl={saved.raw_jsonl_path}")
        if saved.normalized_path:
            print(f"normalized_jsonl={saved.normalized_path}")
        return result.returncode
    if args.command == "compare":
        result = compare_normalized_sequences(read_jsonl(Path(args.expected)), read_jsonl(Path(args.actual)))
        print(result.summary)
        for detail in result.details:
            print(detail)
        return 0 if result.matches else 1
    if args.command == "normalize-exec":
        rows = read_jsonl(Path(args.input))
        normalized = normalize_exec_events(rows)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        from .io import write_jsonl
        write_jsonl(Path(args.output), normalized)
        print(f"normalized {len(rows)} raw events into {len(normalized)} events")
        return 0
    if args.command == "promote-capture":
        example_dir = promote_capture_to_example(
            capture_dir=Path(args.capture_dir),
            output_root=Path(args.output_dir),
            example_id=args.example_id,
            prompt=args.prompt,
        )
        print(f"promoted capture to {example_dir}")
        return 0
    if args.command == "compare-baselines":
        results = compare_capture_against_baselines(
            normalized_path=Path(args.normalized),
            baselines_root=Path(args.baselines_dir),
        )
        matched = [result for result in results if result.matches]
        print(f"matched={len(matched)} total={len(results)}")
        for result in results:
            status = "MATCH" if result.matches else "DIFF"
            print(f"{status} {result.example_id}: {result.summary}")
        return 0 if matched else 1
    if args.command == "observe":
        outcome = observe_prompt(
            prompt=args.prompt,
            profile=args.profile,
            cwd=Path(args.cwd),
            captures_dir=Path(args.captures_dir),
            promote_dir=Path(args.promote_dir),
            baselines_dir=Path(args.baselines_dir),
            example_id=args.example_id,
        )
        print(f"session_dir={outcome.capture.session_dir}")
        if outcome.capture.normalized_path:
            print(f"normalized_jsonl={outcome.capture.normalized_path}")
        if outcome.promoted_example_dir:
            print(f"promoted_example={outcome.promoted_example_dir}")
        if outcome.summary_path:
            print(f"comparison_summary={outcome.summary_path}")
        matched = [item for item in outcome.comparison_results if item.matches]
        print(f"baseline_matches={len(matched)}/{len(outcome.comparison_results)}")
        return 0 if outcome.capture.normalized_path else outcome.capture.meta_path.exists()

    parser.print_help()
    return 0
