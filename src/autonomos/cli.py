"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from .app import run_chat
from .baseline import (
    build_golden_registry,
    compare_capture_against_baselines,
    format_comparison_results,
    import_normalized_trace_as_example,
    promote_capture_to_example,
)
from .codex_families import (
    DEFAULT_CORE_PROMPT_FAMILIES_PATH,
    build_codex_capture_command,
    build_codex_capture_metadata,
    get_core_prompt_family,
    load_core_prompt_families,
)
from .codex_exec import build_exec_command, describe_ws_runtime, render_codex_config_toml
from .compare import compare_normalized_sequences
from .config import load_ws_auth_config
from .delta import analyze_trace_drift, format_drift_analysis
from .examples import build_examples_dataset
from .exec_normalizer import normalize_exec_events
from .io import read_jsonl
from .live_capture import run_capture, save_capture_session, save_capture_snapshot
from .memory import list_sessions
from .orchestration import write_approval_response, write_request_user_input_response
from .review import resolve_review_request
from .regression import (
    DEFAULT_EVAL_SUITE_PATH,
    load_eval_suite,
    run_generalization_suite,
    run_regression_suite,
    write_regression_json,
    write_regression_report,
)
from .scoring import compute_parity_score, format_parity_score
from .verification import format_verification_results, verify_runtime_against_goldens
from .workflow import observe_prompt

DEFAULT_RUNTIME_PROFILE = "roma_ws"
DEFAULT_OBSERVE_PROFILE = "openai_ws"
DEFAULT_RUNTIME_BASELINES_DIR = "goldens"
DEFAULT_OBSERVE_BASELINES_DIR = "examples"


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
    capture_live.add_argument("--profile", default=DEFAULT_OBSERVE_PROFILE, help="Codex profile name.")
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
    compare_baselines.add_argument("--baselines-dir", default=DEFAULT_OBSERVE_BASELINES_DIR, help="Baseline examples directory.")
    compare_baselines.add_argument("--top", type=int, default=5, help="Maximum number of comparisons to print.")

    import_golden = subparsers.add_parser("import-golden", help="Import a normalized trace as a repo-tracked golden example.")
    import_golden.add_argument("normalized", help="Path to normalized JSONL trace.")
    import_golden.add_argument("example_id", help="Golden example id.")
    import_golden.add_argument("prompt", help="Prompt associated with the trace.")
    import_golden.add_argument("--output-dir", default="goldens", help="Directory where golden traces are stored.")

    import_capture_golden = subparsers.add_parser("import-capture-golden", help="Import a saved capture directory as a repo-tracked golden example.")
    import_capture_golden.add_argument("capture_dir", help="Capture session directory containing normalized.jsonl and prompt.txt.")
    import_capture_golden.add_argument("example_id", help="Golden example id.")
    import_capture_golden.add_argument("--output-dir", default="goldens", help="Directory where golden traces are stored.")
    import_capture_golden.add_argument("--prompt", help="Optional prompt override.")

    import_golden_raw = subparsers.add_parser("import-golden-raw", help="Normalize a raw exec trace and import it as a golden example.")
    import_golden_raw.add_argument("raw", help="Path to raw exec JSONL trace.")
    import_golden_raw.add_argument("example_id", help="Golden example id.")
    import_golden_raw.add_argument("prompt", help="Prompt associated with the trace.")
    import_golden_raw.add_argument("--output-dir", default="goldens", help="Directory where golden traces are stored.")

    list_goldens = subparsers.add_parser("list-goldens", help="List repo-tracked golden traces.")
    list_goldens.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")

    show_core_families = subparsers.add_parser("show-core-families", help="List the core Codex prompt families used for live trace capture.")
    show_core_families.add_argument("--families-path", default=str(DEFAULT_CORE_PROMPT_FAMILIES_PATH), help="Path to core prompt family JSON.")

    capture_codex_family = subparsers.add_parser("capture-codex-family", help="Capture a real Codex trace for a configured prompt family.")
    capture_codex_family.add_argument("family_id", help="Configured family id from core_prompt_families.json")
    capture_codex_family.add_argument("--families-path", default=str(DEFAULT_CORE_PROMPT_FAMILIES_PATH), help="Path to core prompt family JSON.")
    capture_codex_family.add_argument("--cwd", default=".", help="Working directory for Codex execution.")
    capture_codex_family.add_argument("--output-dir", default="codex_traces", help="Directory where canonical Codex trace captures are stored.")
    capture_codex_family.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")
    capture_codex_family.add_argument("--promote-to-golden", action="store_true", help="Also import the captured normalized trace into the goldens directory.")
    capture_codex_family.add_argument(
        "--allow-approvals",
        action="store_true",
        help="Do not bypass approvals/sandbox during capture. Use this for families that need real approval artifacts.",
    )
    capture_runtime_family = subparsers.add_parser(
        "capture-runtime-family",
        help="Capture a runtime trace for a configured prompt family, auto-resuming approval or user-input artifacts when they appear.",
    )
    capture_runtime_family.add_argument("family_id", help="Configured family id from core_prompt_families.json")
    capture_runtime_family.add_argument("--families-path", default=str(DEFAULT_CORE_PROMPT_FAMILIES_PATH), help="Path to core prompt family JSON.")
    capture_runtime_family.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    capture_runtime_family.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    capture_runtime_family.add_argument("--output-dir", default="codex_traces", help="Directory where canonical runtime trace captures are stored.")
    capture_runtime_family.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")
    capture_runtime_family.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    capture_runtime_family.add_argument("--captures-dir", default="captures", help="Directory where runtime capture sessions are stored.")
    capture_runtime_family.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    capture_runtime_family.add_argument("--promote-to-golden", action="store_true", help="Also import the captured normalized trace into the goldens directory.")

    analyze_drift = subparsers.add_parser("analyze-drift", help="Explain structured drift between two normalized traces.")
    analyze_drift.add_argument("expected", help="Expected normalized.jsonl path.")
    analyze_drift.add_argument("actual", help="Actual normalized.jsonl path.")

    verify_runtime = subparsers.add_parser("verify-runtime", help="Run representative golden prompts and compare runtime behavior.")
    verify_runtime.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    verify_runtime.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    verify_runtime.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    verify_runtime.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    verify_runtime.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    verify_runtime.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    verify_runtime.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")

    show_eval_suite = subparsers.add_parser("show-eval-suite", help="Print the configured golden regression evaluation suite.")
    show_eval_suite.add_argument("--suite-path", default=str(DEFAULT_EVAL_SUITE_PATH), help="Path to eval suite JSON.")

    run_regression = subparsers.add_parser("run-regression", help="Run the golden regression suite and emit readable reports.")
    run_regression.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    run_regression.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    run_regression.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    run_regression.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    run_regression.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    run_regression.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    run_regression.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")
    run_regression.add_argument("--suite-path", default=str(DEFAULT_EVAL_SUITE_PATH), help="Path to eval suite JSON.")
    run_regression.add_argument("--report-path", default=".tmp/regression/report.md", help="Path to write markdown report.")
    run_regression.add_argument("--json-path", default=".tmp/regression/results.json", help="Path to write JSON results.")

    score_parity = subparsers.add_parser("score-parity", help="Run the regression suite and compute a 10-point Codex parity score.")
    score_parity.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    score_parity.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    score_parity.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    score_parity.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    score_parity.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    score_parity.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    score_parity.add_argument("--goldens-dir", default="goldens", help="Directory where golden traces are stored.")
    score_parity.add_argument("--suite-path", default=str(DEFAULT_EVAL_SUITE_PATH), help="Path to eval suite JSON.")

    run_generalization = subparsers.add_parser("run-generalization", help="Run prompts outside the fixed goldens and summarize how the runtime generalizes.")
    run_generalization.add_argument("prompts", nargs="+", help="One or more prompts to run through the default runtime.")
    run_generalization.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    run_generalization.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    run_generalization.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    run_generalization.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    run_generalization.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    run_generalization.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")

    observe = subparsers.add_parser("observe", help="Run the full observation pipeline: capture, normalize, promote, compare.")
    observe.add_argument("prompt", help="Prompt to send to codex exec.")
    observe.add_argument("--profile", default=DEFAULT_OBSERVE_PROFILE, help="Codex profile name.")
    observe.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    observe.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    observe.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    observe.add_argument("--baselines-dir", default=DEFAULT_OBSERVE_BASELINES_DIR, help="Baseline examples directory.")
    observe.add_argument("--example-id", help="Override promoted example id.")

    chat = subparsers.add_parser("chat", help="Run the user-facing chat flow and print the final assistant answer.")
    chat.add_argument("prompt", nargs="?", help="Prompt to send. If omitted, read from stdin.")
    chat.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    chat.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    chat.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    chat.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    chat.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    chat.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    chat.add_argument("--session-id", default="default", help="Logical chat session id.")
    chat.add_argument("--new-session", action="store_true", help="Generate a fresh session id for this run.")
    chat.add_argument("--request-user-input-response", help="Optional request-user-input response JSON to include on this turn.")

    review = subparsers.add_parser("review", help="Run a review-style chat flow against git changes.")
    review.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    review.add_argument("--cwd", default=".", help="Working directory for git and runtime execution.")
    review.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    review.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    review.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    review.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    review.add_argument("--session-id", default="default", help="Logical chat session id.")
    review.add_argument("--new-session", action="store_true", help="Generate a fresh session id for this run.")
    review_target = review.add_mutually_exclusive_group()
    review_target.add_argument("--base-branch", help="Review changes relative to a base branch.")
    review_target.add_argument("--commit", help="Review a specific commit.")
    review.add_argument("--instructions", help="Custom review instructions.")

    answer_rui = subparsers.add_parser("answer-user-input", help="Write a response file for a request-user-input artifact.")
    answer_rui.add_argument("request_file", help="Path to request-user-input.json")
    answer_rui.add_argument("selected_option", help="Chosen option label.")
    answer_rui.add_argument("--notes", default="", help="Optional notes.")

    answer_approval = subparsers.add_parser("answer-approval", help="Write a response file for an approval-request artifact.")
    answer_approval.add_argument("request_file", help="Path to approval-request.json")
    answer_approval.add_argument("decision", help="Approve or Decline")
    answer_approval.add_argument("--notes", default="", help="Optional notes.")

    resume = subparsers.add_parser("resume", help="Resume a run using a request-user-input response artifact.")
    resume.add_argument("prompt", nargs="?", help="Prompt to send. If omitted, read from stdin.")
    resume.add_argument("--response-file", required=True, help="Path to request-user-input-response.json")
    resume.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    resume.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    resume.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    resume.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    resume.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    resume.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    resume.add_argument("--session-id", default="default", help="Logical chat session id.")
    resume.add_argument("--new-session", action="store_true", help="Generate a fresh session id for this resumed run.")
    resume.add_argument("--approval-response-file", help="Path to approval-response.json")

    transcript = subparsers.add_parser("transcript", help="Print a compact transcript from a normalized session trace.")
    transcript.add_argument("normalized", help="Path to normalized.jsonl")
    transcript.add_argument("--show-deltas", action="store_true", help="Show assistant delta events instead of collapsing them.")

    sessions = subparsers.add_parser("sessions", help="List saved local chat sessions.")
    sessions.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    sessions.add_argument("--latest", action="store_true", help="Print only the most recently active session id.")
    sessions.add_argument("--show-summary", action="store_true", help="Print the latest compact summary line for each session.")

    repl = subparsers.add_parser("repl", help="Run a simple interactive chat loop.")
    repl.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    repl.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    repl.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    repl.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    repl.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    repl.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    repl.add_argument("--session-id", default="default", help="Logical chat session id.")
    repl.add_argument("--new-session", action="store_true", help="Generate a fresh session id for this REPL.")

    tui = subparsers.add_parser("tui", help="Run the interactive Textual TUI.")
    tui.add_argument("--profile", default=DEFAULT_RUNTIME_PROFILE, help="Runtime profile name.")
    tui.add_argument("--cwd", default=".", help="Working directory for runtime execution.")
    tui.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    tui.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    tui.add_argument("--baselines-dir", default=DEFAULT_RUNTIME_BASELINES_DIR, help="Baseline examples directory.")
    tui.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    tui.add_argument("--session-id", default="default", help="Logical chat session id.")
    tui.add_argument("--new-session", action="store_true", help="Generate a fresh session id for the TUI session.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
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
        if args.command == "import-golden":
            example_dir = import_normalized_trace_as_example(
                normalized_path=Path(args.normalized),
                output_root=Path(args.output_dir),
                example_id=args.example_id,
                prompt=args.prompt,
            )
            print(f"imported golden trace to {example_dir}")
            return 0
        if args.command == "import-capture-golden":
            capture_dir = Path(args.capture_dir)
            prompt = args.prompt
            if prompt is None:
                prompt_path = capture_dir / "prompt.txt"
                prompt = prompt_path.read_text(encoding="utf-8").strip()
            example_dir = import_normalized_trace_as_example(
                normalized_path=capture_dir / "normalized.jsonl",
                output_root=Path(args.output_dir),
                example_id=args.example_id,
                prompt=prompt,
                meta={"capture_mode": "golden_trace", "source_capture_dir": str(capture_dir)},
            )
            print(f"imported golden trace to {example_dir}")
            return 0
        if args.command == "import-golden-raw":
            raw_path = Path(args.raw)
            normalized_path = raw_path.with_suffix(".normalized.jsonl")
            from .io import write_jsonl

            write_jsonl(normalized_path, normalize_exec_events(read_jsonl(raw_path)))
            example_dir = import_normalized_trace_as_example(
                normalized_path=normalized_path,
                output_root=Path(args.output_dir),
                example_id=args.example_id,
                prompt=args.prompt,
                meta={"source_raw": str(raw_path)},
            )
            print(f"imported golden trace to {example_dir}")
            return 0
        if args.command == "compare-baselines":
            results = compare_capture_against_baselines(
                normalized_path=Path(args.normalized),
                baselines_root=Path(args.baselines_dir),
            )
            matched = [result for result in results if result.matches]
            print(f"matched={len(matched)} total={len(results)}")
            for line in format_comparison_results(results, limit=args.top):
                print(line)
            return 0 if matched else 1
        if args.command == "list-goldens":
            rows = build_golden_registry(Path(args.goldens_dir))
            for row in rows:
                print(f"{row['example_id']}\t{row['event_count']}\t{row['capture_mode']}\t{row['prompt']}")
            return 0
        if args.command == "show-core-families":
            for family in load_core_prompt_families(Path(args.families_path)):
                print(
                    f"{family.family_id}\t{family.invocation_mode}\t{family.expected_strategy}\t"
                    f"{family.expected_tool_family}\tmax_score={family.max_score}\t{family.prompt}"
                )
            return 0
        if args.command == "capture-codex-family":
            family = get_core_prompt_family(args.family_id, path=Path(args.families_path))
            command = build_codex_capture_command(
                family,
                bypass_approvals_and_sandbox=not args.allow_approvals,
            )
            result = run_capture(command, cwd=Path(args.cwd))
            capture_dir = Path(args.output_dir) / family.family_id
            saved = save_capture_snapshot(
                result=result,
                prompt=family.prompt,
                output_dir=capture_dir,
                capture_mode="codex_exec",
                metadata=build_codex_capture_metadata(family, command),
            )
            print(f"family={family.family_id}")
            print(f"command={' '.join(result.command)}")
            print(f"returncode={result.returncode}")
            print(f"capture_dir={saved.session_dir}")
            if saved.raw_jsonl_path:
                print(f"raw_jsonl={saved.raw_jsonl_path}")
            if saved.normalized_path:
                print(f"normalized_jsonl={saved.normalized_path}")
            if args.promote_to_golden and saved.normalized_path:
                example_dir = import_normalized_trace_as_example(
                    normalized_path=saved.normalized_path,
                    output_root=Path(args.goldens_dir),
                    example_id=family.family_id,
                    prompt=family.prompt,
                    meta={
                        **build_codex_capture_metadata(family, command),
                        "source_raw": str(saved.raw_jsonl_path) if saved.raw_jsonl_path else None,
                        "source_capture_dir": str(saved.session_dir),
                    },
                )
                print(f"golden={example_dir}")
            return result.returncode
        if args.command == "capture-runtime-family":
            family = get_core_prompt_family(args.family_id, path=Path(args.families_path))
            exit_code = _capture_runtime_family(
                family=family,
                profile=args.profile,
                cwd=Path(args.cwd),
                output_dir=Path(args.output_dir),
                goldens_dir=Path(args.goldens_dir),
                memory_dir=Path(args.memory_dir),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                promote_to_golden=args.promote_to_golden,
            )
            return exit_code
        if args.command == "analyze-drift":
            analysis = analyze_trace_drift(
                read_jsonl(Path(args.expected)),
                read_jsonl(Path(args.actual)),
            )
            for line in format_drift_analysis(analysis):
                print(line)
            return 0 if not analysis.primary_causes else 1
        if args.command == "show-eval-suite":
            for case in load_eval_suite(Path(args.suite_path)):
                print(
                    f"{case.example_id}\t{case.expected_strategy}\t{case.expected_tool_family}\t"
                    f"artifact={case.expected_artifact or 'none'}\tmax_score={case.max_score}\t{case.prompt}"
                )
            return 0
        if args.command == "verify-runtime":
            results = verify_runtime_against_goldens(
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                goldens_dir=Path(args.goldens_dir),
            )
            matched = len([result for result in results if result.matched_expected_golden])
            print(f"matched={matched} total={len(results)}")
            for line in format_verification_results(results):
                print(line)
            return 0 if matched == len(results) else 1
        if args.command == "run-regression":
            results = run_regression_suite(
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                goldens_dir=Path(args.goldens_dir),
                suite_path=Path(args.suite_path),
            )
            report_path = write_regression_report(Path(args.report_path), results)
            json_path = write_regression_json(Path(args.json_path), results)
            passed = len([result for result in results if result.passed])
            print(f"passed={passed} total={len(results)}")
            print(f"report={report_path}")
            print(f"json={json_path}")
            for result in results:
                status = "PASS" if result.passed else "FAIL"
                print(
                    f"{status} {result.example_id}: strategy={result.actual_strategy} "
                    f"artifact={'yes' if result.artifact_present else 'no'} "
                    f"expected_score={result.expected_score if result.expected_score is not None else '?'} "
                    f"tool_family={result.actual_tool_family} "
                    f"closest={result.closest_match_example_id or 'none'} "
                    f"score={result.closest_match_score if result.closest_match_score is not None else '?'}"
                )
            return 0 if passed == len(results) else 1
        if args.command == "score-parity":
            results = run_regression_suite(
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                goldens_dir=Path(args.goldens_dir),
                suite_path=Path(args.suite_path),
            )
            score = compute_parity_score(results)
            for line in format_parity_score(score):
                print(line)
            return 0 if score.total_score >= score.max_score else 1
        if args.command == "run-generalization":
            results = run_generalization_suite(
                prompts=args.prompts,
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
            )
            for result in results:
                print(
                    f"prompt={result.prompt}\tstrategy={result.strategy_id}\ttool_family={result.tool_family}\t"
                    f"closest={result.closest_match_example_id or 'none'}\tscore={result.closest_match_score if result.closest_match_score is not None else '?'}"
                )
            return 0
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
        if args.command == "answer-user-input":
            response_path = write_request_user_input_response(
                request_path=Path(args.request_file),
                selected_option=args.selected_option,
                notes=args.notes,
            )
            print(response_path)
            return 0
        if args.command == "answer-approval":
            response_path = write_approval_response(
                request_path=Path(args.request_file),
                decision=args.decision,
                notes=args.notes,
            )
            print(response_path)
            return 0
        if args.command == "chat":
            session_id = _resolve_session_id(args.session_id, args.new_session)
            prompt = args.prompt
            if prompt is None:
                prompt = sys.stdin.read().strip()
            if not prompt:
                print("prompt is required")
                return 2
            summary = run_chat(
                prompt=prompt,
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                session_id=session_id,
                request_user_input_response_path=Path(args.request_user_input_response) if args.request_user_input_response else None,
                approval_response_path=Path(args.approval_response_file) if hasattr(args, "approval_response_file") and args.approval_response_file else None,
            )
            if summary.final_message:
                print(summary.final_message)
            else:
                print("No final assistant message was captured.")
            print(f"[strategy] {summary.strategy_id} -> {_strategy_reference_label(summary)}")
            print(f"[attempts] {', '.join(summary.attempted_strategies)}")
            print(f"[policy] {summary.orchestration_summary}")
            print(f"[session] {summary.session_dir}")
            if summary.normalized_path:
                print(f"[normalized] {summary.normalized_path}")
            if summary.promoted_example_dir:
                print(f"[example] {summary.promoted_example_dir}")
            if summary.comparison_summary_path:
                print(f"[comparison] {summary.comparison_summary_path}")
            if summary.request_user_input_path:
                print(f"[request-user-input] {summary.request_user_input_path}")
            if summary.approval_request_path:
                print(f"[approval-request] {summary.approval_request_path}")
            if summary.memory_path:
                print(f"[memory] {summary.memory_path}")
            print(f"[session-id] {session_id}")
            print(f"[adaptive] {summary.adaptive_notes}")
            _print_parity_summary(summary)
            _print_match_metadata(summary)
            return 0
        if args.command == "review":
            session_id = _resolve_session_id(args.session_id, args.new_session)
            review_request = resolve_review_request(
                cwd=Path(args.cwd),
                base_branch=args.base_branch,
                commit=args.commit,
                instructions=args.instructions,
            )
            summary = run_chat(
                prompt=review_request.prompt,
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                session_id=session_id,
            )
            if summary.final_message:
                print(summary.final_message)
            else:
                print("No final assistant message was captured.")
            print(f"[review-target] {review_request.user_facing_hint}")
            print(f"[strategy] {summary.strategy_id} -> {_strategy_reference_label(summary)}")
            print(f"[attempts] {', '.join(summary.attempted_strategies)}")
            print(f"[policy] {summary.orchestration_summary}")
            print(f"[session] {summary.session_dir}")
            if summary.normalized_path:
                print(f"[normalized] {summary.normalized_path}")
            if summary.promoted_example_dir:
                print(f"[example] {summary.promoted_example_dir}")
            if summary.comparison_summary_path:
                print(f"[comparison] {summary.comparison_summary_path}")
            print(f"[session-id] {session_id}")
            print(f"[adaptive] {summary.adaptive_notes}")
            _print_parity_summary(summary)
            _print_match_metadata(summary)
            return 0
        if args.command == "resume":
            session_id = _resolve_session_id(args.session_id, args.new_session)
            prompt = args.prompt
            if prompt is None:
                prompt = sys.stdin.read().strip()
            if not prompt:
                print("prompt is required")
                return 2
            summary = run_chat(
                prompt=prompt,
                profile=args.profile,
                cwd=Path(args.cwd),
                captures_dir=Path(args.captures_dir),
                promote_dir=Path(args.promote_dir),
                baselines_dir=Path(args.baselines_dir),
                memory_dir=Path(args.memory_dir),
                session_id=session_id,
                request_user_input_response_path=Path(args.response_file),
                approval_response_path=Path(args.approval_response_file) if args.approval_response_file else None,
            )
            if summary.final_message:
                print(summary.final_message)
            else:
                print("No final assistant message was captured.")
            print(f"[strategy] {summary.strategy_id} -> {_strategy_reference_label(summary)}")
            print(f"[attempts] {', '.join(summary.attempted_strategies)}")
            print(f"[policy] {summary.orchestration_summary}")
            print(f"[session] {summary.session_dir}")
            if summary.request_user_input_path:
                print(f"[request-user-input] {summary.request_user_input_path}")
            if summary.approval_request_path:
                print(f"[approval-request] {summary.approval_request_path}")
            if summary.memory_path:
                print(f"[memory] {summary.memory_path}")
            print(f"[session-id] {session_id}")
            print(f"[adaptive] {summary.adaptive_notes}")
            _print_parity_summary(summary)
            _print_match_metadata(summary)
            return 0
        if args.command == "transcript":
            _print_transcript(read_jsonl(Path(args.normalized)), show_deltas=args.show_deltas)
            return 0
        if args.command == "sessions":
            rows = list_sessions(Path(args.memory_dir))
            if args.latest:
                if rows:
                    print(rows[0][0])
                return 0
            for index, (session_id, count, last_ts) in enumerate(rows):
                marker = "*" if index == 0 else " "
                line = f"{marker}\t{session_id}\t{count}\t{last_ts or '-'}"
                if args.show_summary:
                    summary = _read_session_summary(Path(args.memory_dir), session_id)
                    if summary:
                        line += f"\t{summary}"
                print(line)
            return 0
        if args.command == "repl":
            session_id = _resolve_session_id(args.session_id, args.new_session)
            print("Autonomos REPL. Type /exit to quit.")
            print(f"[session-id] {session_id}")
            while True:
                try:
                    prompt = input("> ").strip()
                except EOFError:
                    break
                if not prompt:
                    continue
                if prompt in {"/exit", "/quit"}:
                    break
                if prompt == "/sessions":
                    for index, (sid, count, last_ts) in enumerate(list_sessions(Path(args.memory_dir))):
                        marker = "*" if sid == session_id else ("+" if index == 0 else " ")
                        print(f"{marker}\t{sid}\t{count}\t{last_ts or '-'}")
                    continue
                if prompt == "/context":
                    _print_session_context(Path(args.memory_dir), session_id)
                    continue
                summary = run_chat(
                    prompt=prompt,
                    profile=args.profile,
                    cwd=Path(args.cwd),
                    captures_dir=Path(args.captures_dir),
                    promote_dir=Path(args.promote_dir),
                    baselines_dir=Path(args.baselines_dir),
                    memory_dir=Path(args.memory_dir),
                    session_id=session_id,
                )
                _print_repl_summary(summary)
                follow_up = _handle_repl_follow_up(
                    summary=summary,
                    profile=args.profile,
                    cwd=Path(args.cwd),
                    captures_dir=Path(args.captures_dir),
                    promote_dir=Path(args.promote_dir),
                    baselines_dir=Path(args.baselines_dir),
                    memory_dir=Path(args.memory_dir),
                    session_id=session_id,
                )
                if follow_up is not None:
                    _print_repl_summary(follow_up)
            return 0
        if args.command == "tui":
            session_id = _resolve_tui_session_id(args.session_id, args.new_session)
            from .tui_app import TuiConfig, run_tui

            run_tui(
                TuiConfig(
                    profile=args.profile,
                    cwd=Path(args.cwd),
                    captures_dir=Path(args.captures_dir),
                    promote_dir=Path(args.promote_dir),
                    baselines_dir=Path(args.baselines_dir),
                    memory_dir=Path(args.memory_dir),
                    session_id=session_id,
                )
            )
            return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    parser.print_help()
    return 0


def _handle_inline_request_user_input(request_path: Path) -> Path | None:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    if not questions:
        return None
    question = questions[0]
    print(question.get("question", "Choose an option:"))
    options = question.get("options", [])
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option.get('label')} - {option.get('description')}")
    choice = input("selection [1]: ").strip() or "1"
    try:
        selected = options[max(0, int(choice) - 1)]["label"]
    except (ValueError, IndexError, KeyError):
        selected = options[0]["label"] if options else "default"
    notes = input("notes (optional): ").strip()
    return write_request_user_input_response(
        request_path=request_path,
        selected_option=selected,
        notes=notes,
    )


def _write_default_request_user_input_response(request_path: Path) -> Path:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    question = questions[0] if questions else {}
    options = question.get("options", [])
    selected = options[0]["label"] if options else "default"
    return write_request_user_input_response(
        request_path=request_path,
        selected_option=selected,
        notes="Auto-selected during runtime family capture.",
    )


def _write_default_approval_response(request_path: Path) -> Path:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    options = payload.get("options", [])
    selected = options[0]["label"] if options else "Approve"
    return write_approval_response(
        request_path=request_path,
        decision=selected,
        notes="Auto-approved during runtime family capture.",
    )


def _capture_runtime_family(
    *,
    family,
    profile: str,
    cwd: Path,
    output_dir: Path,
    goldens_dir: Path,
    memory_dir: Path,
    captures_dir: Path,
    promote_dir: Path,
    promote_to_golden: bool,
) -> int:
    session_id = f"capture-{family.family_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    saw_approval_request = False
    saw_request_user_input = False
    summary = run_chat(
        prompt=family.prompt,
        profile=profile,
        cwd=cwd,
        captures_dir=captures_dir / family.family_id,
        promote_dir=promote_dir / family.family_id,
        baselines_dir=goldens_dir,
        memory_dir=memory_dir,
        session_id=session_id,
        target_example_id=family.family_id,
    )
    if summary.request_user_input_path:
        saw_request_user_input = True
        response_path = _write_default_request_user_input_response(summary.request_user_input_path)
        summary = run_chat(
            prompt="continue",
            profile=profile,
            cwd=cwd,
            captures_dir=captures_dir / family.family_id,
            promote_dir=promote_dir / family.family_id,
            baselines_dir=goldens_dir,
            memory_dir=memory_dir,
            session_id=session_id,
            request_user_input_response_path=response_path,
            target_example_id=family.family_id,
        )
    if summary.approval_request_path:
        saw_approval_request = True
        response_path = _write_default_approval_response(summary.approval_request_path)
        summary = run_chat(
            prompt="continue",
            profile=profile,
            cwd=cwd,
            captures_dir=captures_dir / family.family_id,
            promote_dir=promote_dir / family.family_id,
            baselines_dir=goldens_dir,
            memory_dir=memory_dir,
            session_id=session_id,
            approval_response_path=response_path,
            target_example_id=family.family_id,
        )
    capture_dir = output_dir / family.family_id
    if capture_dir.exists():
        shutil.rmtree(capture_dir)
    shutil.copytree(summary.session_dir, capture_dir)
    meta_path = capture_dir / "meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(
        {
            **build_codex_capture_metadata(family, ["autonomos", "capture-runtime-family", family.family_id]),
            "capture_mode": "runtime_chat",
            "source_capture_dir": str(summary.session_dir),
            "session_id": session_id,
            "approval_request_present": saw_approval_request or summary.approval_request_path is not None,
            "request_user_input_present": saw_request_user_input or summary.request_user_input_path is not None,
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"family={family.family_id}")
    print(f"session_id={session_id}")
    print(f"capture_dir={capture_dir}")
    if summary.normalized_path:
        print(f"normalized_jsonl={capture_dir / 'normalized.jsonl'}")
    if saw_approval_request or summary.approval_request_path:
        print("approval_artifact=present")
    if saw_request_user_input or summary.request_user_input_path:
        print("request_user_input_artifact=present")
    if promote_to_golden and summary.normalized_path:
        example_dir = import_normalized_trace_as_example(
            normalized_path=capture_dir / "normalized.jsonl",
            output_root=goldens_dir,
            example_id=family.family_id,
            prompt=family.prompt,
            meta=meta,
        )
        print(f"golden={example_dir}")
    return 0


def _handle_inline_approval(request_path: Path) -> Path | None:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    print(payload.get("question", "Approve?"))
    options = payload.get("options", [])
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option.get('label')} - {option.get('description')}")
    choice = input("selection [1]: ").strip() or "1"
    try:
        selected = options[max(0, int(choice) - 1)]["label"]
    except (ValueError, IndexError, KeyError):
        selected = options[0]["label"] if options else "Approve"
    notes = input("notes (optional): ").strip()
    return write_approval_response(
        request_path=request_path,
        decision=selected,
        notes=notes,
    )


def _print_repl_summary(summary) -> None:
    if summary.final_message:
        print(summary.final_message)
    else:
        print("No final assistant message was captured.")
    print(f"[strategy] {summary.strategy_id} -> {_strategy_reference_label(summary)}")
    print(f"[policy] {summary.orchestration_summary}")
    if summary.request_user_input_path:
        print(f"[request-user-input] {summary.request_user_input_path}")
    if summary.approval_request_path:
        print(f"[approval-request] {summary.approval_request_path}")
    _print_match_metadata(summary)


def _handle_repl_follow_up(
    *,
    summary,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path,
    baselines_dir: Path,
    memory_dir: Path,
    session_id: str,
):
    approval_response = None
    user_input_response = None
    if summary.approval_request_path:
        approval_response = _handle_inline_approval(summary.approval_request_path)
        if approval_response:
            print(f"[approval] {approval_response}")
    if summary.request_user_input_path:
        user_input_response = _handle_inline_request_user_input(summary.request_user_input_path)
        if user_input_response:
            print(f"[request-user-input] {user_input_response}")
    if approval_response is None and user_input_response is None:
        return None
    return run_chat(
        prompt="continue",
        profile=profile,
        cwd=cwd,
        captures_dir=captures_dir,
        promote_dir=promote_dir,
        baselines_dir=baselines_dir,
        memory_dir=memory_dir,
        session_id=session_id,
        request_user_input_response_path=user_input_response,
        approval_response_path=approval_response,
    )


def _print_match_metadata(summary) -> None:
    intended_id = getattr(summary, "intended_match_example_id", None)
    intended_score = getattr(summary, "intended_match_score", None)
    if intended_id is not None:
        print(f"[intended-golden] {intended_id} (score={intended_score})")
    closest_id = getattr(summary, "closest_match_example_id", None)
    closest_score = getattr(summary, "closest_match_score", None)
    if closest_id is not None:
        print(f"[closest-match] {closest_id} (score={closest_score})")
    drift_summary = getattr(summary, "drift_summary", None)
    drift_primary_causes = getattr(summary, "drift_primary_causes", [])
    if drift_summary:
        print(f"[drift] {drift_summary}")
    elif intended_id is not None and intended_score == 0:
        print("[drift] aligned")
    if drift_primary_causes:
        print(f"[drift-causes] {', '.join(drift_primary_causes)}")
    validation_hints = getattr(summary, "validation_hints", [])
    for hint in validation_hints:
        print(f"[validation] {hint}")
    runtime_diagnostics = getattr(summary, "runtime_diagnostics", [])
    if runtime_diagnostics:
        print(f"[runtime] {'; '.join(runtime_diagnostics)}")


def _print_parity_summary(summary) -> None:
    intended_id = getattr(summary, "intended_match_example_id", None)
    intended_score = getattr(summary, "intended_match_score", None)
    closest_id = getattr(summary, "closest_match_example_id", None)
    closest_score = getattr(summary, "closest_match_score", None)
    if intended_id is not None and intended_score is not None:
        if intended_score == 0:
            print(f"[parity] exact match for {intended_id}")
        else:
            print(f"[parity] drift from {intended_id} (score={intended_score})")
    elif closest_id is not None and closest_score is not None:
        print(f"[parity] closest golden is {closest_id} (score={closest_score})")
    print(f"[coverage] {summary.baseline_matches}/{summary.baseline_total} aligned traces")


def _strategy_reference_label(summary) -> str:
    intended_id = getattr(summary, "intended_match_example_id", None)
    if intended_id:
        return intended_id
    closest_id = getattr(summary, "closest_match_example_id", None)
    if closest_id:
        return closest_id
    return getattr(summary, "baseline_example_id", "unknown")


def _print_transcript(rows: list[dict], *, show_deltas: bool) -> None:
    pending_delta = None
    final_message = None
    for row in rows:
        event_type = row.get("event_type")
        payload = row.get("payload", {})
        if event_type == "assistant_message_delta" and not show_deltas:
            pending_delta = payload.get("text", "")
            continue
        if event_type == "status_update":
            print(f"status> {payload.get('text', '')}")
            continue
        if event_type == "assistant_message":
            if pending_delta and pending_delta != payload.get("text", ""):
                print(f"assistant~ {pending_delta}")
            text = payload.get("text", "")
            print(f"assistant> {text}")
            final_message = text
            pending_delta = None
        elif event_type == "assistant_message_delta":
            print(f"assistant~ {payload.get('text', '')}")
        elif event_type == "user_input":
            print(f"user> {payload.get('text', '')}")
        elif event_type and "tool" in event_type:
            tool_name = payload.get("tool_name", "unknown")
            if event_type == "tool_call_request":
                print(f"tool> request {tool_name} {payload.get('args', {})}")
            elif event_type == "tool_call_result":
                output = str(payload.get("output", ""))
                print(f"tool> result {tool_name} {output[:160]}")
            else:
                print(f"tool> {event_type} {payload}")
        else:
            print(f"event> {event_type}")
    if final_message:
        print(f"final> {final_message}")


def _resolve_session_id(session_id: str, new_session: bool) -> str:
    if not new_session:
        return session_id
    return datetime.now(UTC).strftime("session-%Y%m%dT%H%M%SZ")


def _resolve_tui_session_id(session_id: str, new_session: bool) -> str:
    if new_session or session_id != "default":
        return _resolve_session_id(session_id, new_session)
    return _resolve_session_id("default", True)


def _read_session_summary(memory_dir: Path, session_id: str) -> str | None:
    path = memory_dir / f"{session_id}.jsonl"
    if not path.exists():
        return None
    rows = read_jsonl(path)
    for row in reversed(rows):
        if row.get("role") == "summary":
            text = str(row.get("text", "")).splitlines()
            return text[0] if text else None
    return None


def _print_session_context(memory_dir: Path, session_id: str) -> None:
    path = memory_dir / f"{session_id}.jsonl"
    if not path.exists():
        print("No saved session context.")
        return
    rows = read_jsonl(path)
    for row in rows[-8:]:
        role = row.get("role", "unknown")
        text = str(row.get("text", "")).strip()
        print(f"{role}> {text}")
