"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .app import run_chat
from .baseline import compare_capture_against_baselines, promote_capture_to_example
from .codex_exec import build_exec_command, describe_ws_runtime, render_codex_config_toml
from .compare import compare_normalized_sequences
from .config import load_ws_auth_config
from .examples import build_examples_dataset
from .exec_normalizer import normalize_exec_events
from .io import read_jsonl
from .live_capture import run_capture, save_capture_session
from .memory import list_sessions
from .orchestration import write_approval_response, write_request_user_input_response
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

    chat = subparsers.add_parser("chat", help="Run the user-facing chat flow and print the final assistant answer.")
    chat.add_argument("prompt", nargs="?", help="Prompt to send. If omitted, read from stdin.")
    chat.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    chat.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    chat.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    chat.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    chat.add_argument("--baselines-dir", default="examples", help="Baseline examples directory.")
    chat.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    chat.add_argument("--session-id", default="default", help="Logical chat session id.")
    chat.add_argument("--request-user-input-response", help="Optional request-user-input response JSON to include on this turn.")

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
    resume.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    resume.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    resume.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    resume.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    resume.add_argument("--baselines-dir", default="examples", help="Baseline examples directory.")
    resume.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    resume.add_argument("--session-id", default="default", help="Logical chat session id.")
    resume.add_argument("--approval-response-file", help="Path to approval-response.json")

    transcript = subparsers.add_parser("transcript", help="Print a compact transcript from a normalized session trace.")
    transcript.add_argument("normalized", help="Path to normalized.jsonl")

    sessions = subparsers.add_parser("sessions", help="List saved local chat sessions.")
    sessions.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")

    repl = subparsers.add_parser("repl", help="Run a simple interactive chat loop.")
    repl.add_argument("--profile", default="openai_ws", help="Codex profile name.")
    repl.add_argument("--cwd", default=".", help="Working directory for codex exec.")
    repl.add_argument("--captures-dir", default="captures", help="Directory where capture sessions are stored.")
    repl.add_argument("--promote-dir", default="examples_live", help="Directory where promoted examples are stored.")
    repl.add_argument("--baselines-dir", default="examples", help="Baseline examples directory.")
    repl.add_argument("--memory-dir", default=".autonomos/memory", help="Directory where local session memory is stored.")
    repl.add_argument("--session-id", default="default", help="Logical chat session id.")
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
                session_id=args.session_id,
                request_user_input_response_path=Path(args.request_user_input_response) if args.request_user_input_response else None,
                approval_response_path=Path(args.approval_response_file) if hasattr(args, "approval_response_file") and args.approval_response_file else None,
            )
            if summary.final_message:
                print(summary.final_message)
            else:
                print("No final assistant message was captured.")
            print(f"[strategy] {summary.strategy_id} -> {summary.baseline_example_id}")
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
            print(f"[adaptive] {summary.adaptive_notes}")
            print(f"[baseline] {summary.baseline_matches}/{summary.baseline_total} matched")
            return 0
        if args.command == "resume":
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
                session_id=args.session_id,
                request_user_input_response_path=Path(args.response_file),
                approval_response_path=Path(args.approval_response_file) if args.approval_response_file else None,
            )
            if summary.final_message:
                print(summary.final_message)
            else:
                print("No final assistant message was captured.")
            print(f"[strategy] {summary.strategy_id} -> {summary.baseline_example_id}")
            print(f"[attempts] {', '.join(summary.attempted_strategies)}")
            print(f"[policy] {summary.orchestration_summary}")
            print(f"[session] {summary.session_dir}")
            if summary.request_user_input_path:
                print(f"[request-user-input] {summary.request_user_input_path}")
            if summary.approval_request_path:
                print(f"[approval-request] {summary.approval_request_path}")
            if summary.memory_path:
                print(f"[memory] {summary.memory_path}")
            print(f"[adaptive] {summary.adaptive_notes}")
            print(f"[baseline] {summary.baseline_matches}/{summary.baseline_total} matched")
            return 0
        if args.command == "transcript":
            rows = read_jsonl(Path(args.normalized))
            for row in rows:
                event_type = row.get("event_type")
                payload = row.get("payload", {})
                if event_type == "assistant_message":
                    print(f"assistant> {payload.get('text', '')}")
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
            return 0
        if args.command == "sessions":
            rows = list_sessions(Path(args.memory_dir))
            for session_id, count, last_ts in rows:
                print(f"{session_id}\t{count}\t{last_ts or '-'}")
            return 0
        if args.command == "repl":
            print("Autonomos REPL. Type /exit to quit.")
            while True:
                try:
                    prompt = input("> ").strip()
                except EOFError:
                    break
                if not prompt:
                    continue
                if prompt in {"/exit", "/quit"}:
                    break
                summary = run_chat(
                    prompt=prompt,
                    profile=args.profile,
                    cwd=Path(args.cwd),
                    captures_dir=Path(args.captures_dir),
                    promote_dir=Path(args.promote_dir),
                    baselines_dir=Path(args.baselines_dir),
                    memory_dir=Path(args.memory_dir),
                    session_id=args.session_id,
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
                    session_id=args.session_id,
                )
                if follow_up is not None:
                    _print_repl_summary(follow_up)
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
    print(f"[strategy] {summary.strategy_id} -> {summary.baseline_example_id}")
    print(f"[policy] {summary.orchestration_summary}")
    if summary.request_user_input_path:
        print(f"[request-user-input] {summary.request_user_input_path}")
    if summary.approval_request_path:
        print(f"[approval-request] {summary.approval_request_path}")


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
