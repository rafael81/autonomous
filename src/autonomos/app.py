"""User-facing CLI application flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adaptive import AdaptiveSummary, summarize_attempt_progress
from .baseline import (
    BaselineComparison,
    best_comparison_match,
    compare_capture_against_baselines,
    find_examples_for_prompt,
    format_comparison_results,
    promote_capture_to_example,
)
from .delta import analyze_trace_drift
from .instructions import build_full_instructions, render_user_request
from .io import read_jsonl
from .memory import MemoryTurn, append_session_memory, load_session_memory, render_memory_context
from .orchestration import (
    build_retry_appendix,
    decide_orchestration,
    render_approval_response,
    render_request_user_input_response,
    write_approval_artifact,
    write_request_user_input_artifact,
)
from .policy import infer_prompt_policy, is_empty_runtime_fallback, rank_roma_attempt
from .postprocess import codexify_message
from .reports import build_report
from .roma_runtime import RomaAttemptResult, run_roma_chat
from .strategy import candidate_strategies
from .workflow import ObservationRunResult, observe_prompt, slugify_prompt


@dataclass(frozen=True)
class ChatRunSummary:
    final_message: str | None
    strategy_id: str
    baseline_example_id: str
    attempted_strategies: list[str]
    orchestration_summary: str
    session_dir: Path
    normalized_path: Path | None
    promoted_example_dir: Path | None
    baseline_matches: int
    baseline_total: int
    comparison_summary_path: Path | None
    request_user_input_path: Path | None
    adaptive_notes: str
    memory_path: Path | None
    approval_request_path: Path | None
    closest_match_example_id: str | None
    closest_match_score: int | None
    intended_match_example_id: str | None
    intended_match_score: int | None
    drift_summary: str | None
    drift_primary_causes: list[str]
    validation_hints: list[str]
    runtime_diagnostics: list[str]


def run_chat(
    *,
    prompt: str,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path,
    baselines_dir: Path,
    memory_dir: Path,
    session_id: str,
    request_user_input_response_path: Path | None = None,
    approval_response_path: Path | None = None,
    target_example_id: str | None = None,
) -> ChatRunSummary:
    memory_turns = load_session_memory(memory_dir, session_id)
    memory_path = None
    resolved_target_example_id = _default_target_example_id(
        prompt=prompt,
        baselines_dir=baselines_dir,
        target_example_id=target_example_id,
    )
    if profile == "roma_ws":
        attempts: list[RomaAttemptResult] = []
        retry_appendix = ""
        user_input_prefix = render_request_user_input_response(request_user_input_response_path)
        approval_prefix = render_approval_response(approval_response_path)
        memory_prefix = render_memory_context(memory_turns)
        prompt_matched_examples = find_examples_for_prompt(baselines_dir, prompt) if baselines_dir.exists() else []
        for attempt_index, strategy in enumerate(candidate_strategies(prompt), start=1):
            policy = infer_prompt_policy(prompt, strategy)
            instructions = build_full_instructions(strategy, policy)
            steered_prompt = (
                memory_prefix
                + approval_prefix
                + user_input_prefix
                + render_user_request(prompt)
                + retry_appendix
            )
            result = run_roma_chat(
                prompt=steered_prompt,
                history=memory_turns,
                captures_dir=captures_dir / f"attempt-{attempt_index}-{strategy.strategy_id}",
                cwd=cwd,
                instructions=memory_prefix + instructions,
                enable_tools=strategy.strategy_id == "tool_oriented",
                policy=policy,
            )
            comparison_results = (
                compare_capture_against_baselines(
                    normalized_path=result.normalized_path,
                    baselines_root=baselines_dir,
                )
                if baselines_dir.exists() and result.normalized_path.exists()
                else []
            )
            orchestration = decide_orchestration(
                strategy=strategy,
                comparison_results=comparison_results,
                has_normalized_output=result.normalized_path.exists(),
                prompt=prompt,
            )
            intended_match = _resolve_intended_match(
                comparison_results=comparison_results,
                prompt_matched_examples=prompt_matched_examples,
                target_example_id=resolved_target_example_id,
            )
            closest_match = intended_match or best_comparison_match(comparison_results)
            attempts.append(
                RomaAttemptResult(
                    result=result,
                    strategy=strategy,
                    comparison_score=min((item.score for item in comparison_results), default=10_000),
                    comparison_matches=len([item for item in comparison_results if item.matches]),
                    prompt_match_score=min(
                        (item.score for item in comparison_results if item.example_id in prompt_matched_examples),
                        default=10_000,
                    ),
                    preferred_match_score=min(
                        (item.score for item in comparison_results if item.example_id == resolved_target_example_id),
                        default=10_000,
                    ),
                )
            )
            if _should_short_circuit_roma_attempts(prompt=prompt, attempt=attempts[-1]):
                break
            retry_appendix = build_retry_appendix(
                orchestration.retry_reason,
                closest_match_example_id=closest_match.example_id if closest_match else None,
                closest_match_score=closest_match.score if closest_match else None,
            )
            if any(item.matches for item in comparison_results):
                break

        best_attempt = min(attempts, key=lambda item: rank_roma_attempt(prompt, item))
        strategy = best_attempt.strategy
        result = best_attempt.result
        final_message = codexify_message(extract_final_message(result.normalized_path) or result.final_message)
        comparison_results = (
            compare_capture_against_baselines(
                normalized_path=result.normalized_path,
                baselines_root=baselines_dir,
            )
            if baselines_dir.exists() and result.normalized_path.exists()
            else []
        )
        orchestration = decide_orchestration(
            strategy=strategy,
            comparison_results=comparison_results,
            has_normalized_output=result.normalized_path.exists(),
            prompt=prompt,
        )
        adaptive_summary: AdaptiveSummary = summarize_attempt_progress(
            [
                compare_capture_against_baselines(
                    normalized_path=attempt.result.normalized_path,
                    baselines_root=baselines_dir,
                )
                if baselines_dir.exists() and attempt.result.normalized_path.exists()
                else []
                for attempt in attempts
            ]
        )
        request_user_input_path = None
        approval_request_path = None
        intended_match = _resolve_intended_match(
            comparison_results=comparison_results,
            prompt_matched_examples=prompt_matched_examples,
            target_example_id=resolved_target_example_id,
        )
        closest_match = intended_match or best_comparison_match(comparison_results)
        drift_summary, drift_primary_causes = _build_drift_summary(
            baselines_dir=baselines_dir,
            normalized_path=result.normalized_path,
            intended_match_example_id=intended_match.example_id if intended_match else None,
            intended_match_score=intended_match.score if intended_match else None,
        )
        if orchestration.requires_approval:
            approval_request_path = write_approval_artifact(session_dir=result.session_dir, prompt=prompt)
        if orchestration.should_request_user_input:
            request_user_input_path = write_request_user_input_artifact(session_dir=result.session_dir, prompt=prompt)
        if final_message:
            memory_path = append_session_memory(
                memory_dir,
                session_id,
                [MemoryTurn(role="user", text=prompt), MemoryTurn(role="assistant", text=final_message)],
            )
        promoted_example_dir = None
        comparison_summary_path = None
        if result.normalized_path.exists():
            if promote_dir:
                promoted_example_dir = promote_capture_to_example(
                    capture_dir=result.session_dir,
                    output_root=promote_dir,
                    example_id=slugify_prompt(prompt),
                    prompt=prompt,
                )
            comparison_summary_path = result.session_dir / "comparison-summary.md"
            comparison_summary_path.write_text(
                build_report(
                    example_id=slugify_prompt(prompt),
                    prompt=prompt,
                    normalized_events=read_jsonl(result.normalized_path),
                    notes=(
                        f"strategy={strategy.strategy_id}; "
                        f"attempts={[attempt.strategy.strategy_id for attempt in attempts]}; "
                        f"policy={orchestration.policy_summary}; "
                        f"adaptive={adaptive_summary.notes}; "
                        f"intended_match={intended_match.example_id if intended_match else 'none'} "
                        f"score={intended_match.score if intended_match else 'none'}; "
                        f"drift={drift_summary or 'aligned'}; "
                        f"closest_match={closest_match.example_id if closest_match else 'none'}; "
                        f"top_comparisons={format_comparison_results(comparison_results, limit=3)}"
                    ),
                )
                + "\n",
                encoding="utf-8",
            )
        return ChatRunSummary(
            final_message=final_message,
            strategy_id=strategy.strategy_id,
            baseline_example_id=strategy.baseline_example_id,
            attempted_strategies=[attempt.strategy.strategy_id for attempt in attempts],
            orchestration_summary=orchestration.policy_summary,
            session_dir=result.session_dir,
            normalized_path=result.normalized_path,
            promoted_example_dir=promoted_example_dir,
            baseline_matches=len([item for item in comparison_results if item.matches]),
            baseline_total=len(comparison_results),
            comparison_summary_path=comparison_summary_path,
            request_user_input_path=request_user_input_path,
            adaptive_notes=adaptive_summary.notes,
            memory_path=memory_path,
            approval_request_path=approval_request_path,
            closest_match_example_id=closest_match.example_id if closest_match else None,
            closest_match_score=closest_match.score if closest_match else None,
            intended_match_example_id=intended_match.example_id if intended_match else None,
            intended_match_score=intended_match.score if intended_match else None,
            drift_summary=drift_summary,
            drift_primary_causes=drift_primary_causes,
            validation_hints=_suggest_validation_hints(prompt=prompt, final_message=final_message, cwd=cwd),
            runtime_diagnostics=_collect_runtime_diagnostics(result.normalized_path),
        )

    outcome: ObservationRunResult = observe_prompt(
        prompt=prompt,
        profile=profile,
        cwd=cwd,
        captures_dir=captures_dir,
        promote_dir=promote_dir,
        baselines_dir=baselines_dir,
        memory_turns=memory_turns,
        request_user_input_response_path=request_user_input_response_path,
        approval_response_path=approval_response_path,
    )
    final_message = codexify_message(extract_final_message(outcome.capture.normalized_path))
    baseline_matches = len([item for item in outcome.comparison_results if item.matches])
    if final_message:
        memory_path = append_session_memory(
            memory_dir,
            session_id,
            [MemoryTurn(role="user", text=prompt), MemoryTurn(role="assistant", text=final_message)],
        )
    prompt_matched_examples = find_examples_for_prompt(baselines_dir, prompt) if baselines_dir.exists() else []
    intended_match = _resolve_intended_match(
        comparison_results=outcome.comparison_results,
        prompt_matched_examples=prompt_matched_examples,
        target_example_id=target_example_id,
    )
    closest_match = intended_match or best_comparison_match(outcome.comparison_results)
    drift_summary, drift_primary_causes = _build_drift_summary(
        baselines_dir=baselines_dir,
        normalized_path=outcome.capture.normalized_path,
        intended_match_example_id=intended_match.example_id if intended_match else None,
        intended_match_score=intended_match.score if intended_match else None,
    )
    return ChatRunSummary(
        final_message=final_message,
        strategy_id=outcome.strategy.strategy_id,
        baseline_example_id=outcome.strategy.baseline_example_id,
        attempted_strategies=outcome.attempted_strategies,
        orchestration_summary=outcome.orchestration.policy_summary,
        session_dir=outcome.capture.session_dir,
        normalized_path=outcome.capture.normalized_path,
        promoted_example_dir=outcome.promoted_example_dir,
        baseline_matches=baseline_matches,
        baseline_total=len(outcome.comparison_results),
        comparison_summary_path=outcome.summary_path,
        request_user_input_path=outcome.request_user_input_path,
        adaptive_notes=outcome.adaptive_summary.notes,
        memory_path=memory_path,
        approval_request_path=outcome.approval_request_path,
        closest_match_example_id=closest_match.example_id if closest_match else None,
        closest_match_score=closest_match.score if closest_match else None,
        intended_match_example_id=intended_match.example_id if intended_match else None,
        intended_match_score=intended_match.score if intended_match else None,
        drift_summary=drift_summary,
        drift_primary_causes=drift_primary_causes,
    )


def extract_final_message(normalized_path: Path | None) -> str | None:
    if normalized_path is None or not normalized_path.exists():
        return None
    rows = read_jsonl(normalized_path)
    for row in reversed(rows):
        if row["event_type"] == "assistant_message":
            text = row["payload"].get("text")
            if is_empty_runtime_fallback(text):
                synthesized = _synthesize_from_tool_results(rows)
                return synthesized or text
            return text
    return None


def _synthesize_from_tool_results(rows: list[dict]) -> str | None:
    tool_results = [row for row in rows if row.get("event_type") == "tool_call_result"]
    if not tool_results:
        return None
    lines = ["Observed workspace structure:"]
    for row in tool_results[:4]:
        tool_name = row["payload"].get("tool_name", "tool")
        output = str(row["payload"].get("output", "")).strip()
        if not output:
            continue
        preview_lines = output.splitlines()[:4]
        preview = "; ".join(preview_lines)
        lines.append(f"- {tool_name}: {preview}")
    if len(lines) == 1:
        return None
    return "\n".join(lines)


def _should_short_circuit_roma_attempts(*, prompt: str, attempt: RomaAttemptResult) -> bool:
    policy = infer_prompt_policy(prompt, attempt.strategy)
    if policy.prompt_mode != "general":
        return False
    if attempt.strategy.strategy_id != "simple_answer":
        return False
    rows = read_jsonl(attempt.result.normalized_path) if attempt.result.normalized_path.exists() else []
    has_tool_events = any(row.get("event_type") in {"tool_call_request", "tool_call_result"} for row in rows)
    final_message = extract_final_message(attempt.result.normalized_path)
    return bool(final_message) and not has_tool_events and not is_empty_runtime_fallback(final_message)


def _resolve_intended_match(
    *,
    comparison_results: list[BaselineComparison],
    prompt_matched_examples: list[str],
    target_example_id: str | None,
) -> BaselineComparison | None:
    if target_example_id:
        for result in comparison_results:
            if result.example_id == target_example_id:
                return result
    if not prompt_matched_examples:
        return None
    prompt_matched_results = [item for item in comparison_results if item.example_id in prompt_matched_examples]
    return best_comparison_match(prompt_matched_results)


def _default_target_example_id(*, prompt: str, baselines_dir: Path, target_example_id: str | None) -> str | None:
    if target_example_id:
        return target_example_id
    policy = infer_prompt_policy(prompt)
    if policy.prompt_mode == "status_summary":
        candidate = "codex-status-summary"
        if (baselines_dir / candidate / "normalized.jsonl").exists():
            return candidate
    return None


def _build_drift_summary(
    *,
    baselines_dir: Path,
    normalized_path: Path | None,
    intended_match_example_id: str | None,
    intended_match_score: int | None,
) -> tuple[str | None, list[str]]:
    if (
        intended_match_example_id is None
        or intended_match_score is None
        or intended_match_score == 0
        or normalized_path is None
        or not normalized_path.exists()
    ):
        return (None, [])
    expected_path = baselines_dir / intended_match_example_id / "normalized.jsonl"
    if not expected_path.exists():
        return (None, [])
    analysis = analyze_trace_drift(read_jsonl(expected_path), read_jsonl(normalized_path))
    if not analysis.categories:
        return (None, [])
    return (analysis.summary, analysis.primary_causes)


def _suggest_validation_hints(*, prompt: str, final_message: str | None, cwd: Path) -> list[str]:
    text = prompt.lower()
    hints: list[str] = []
    if "review" in text or "current code changes" in text or "diff" in text:
        if (cwd / "tests").exists():
            hints.append("Run `./.venv/bin/python -m pytest -q` to validate the reviewed changes against the test suite.")
        if (cwd / "pyproject.toml").exists():
            hints.append("Re-run the affected command path after applying fixes to confirm the top finding is resolved.")
    if final_message and ("implement" in text or "change" in text or "fix" in text):
        hints.append("Validate the touched behavior with the narrowest reproducible command before broad regression runs.")
    return hints


def _collect_runtime_diagnostics(normalized_path: Path | None) -> list[str]:
    if normalized_path is None or not normalized_path.exists():
        return ["missing normalized trace"]
    rows = read_jsonl(normalized_path)
    diagnostics: list[str] = []
    if any(row.get("event_type") == "assistant_message_delta" for row in rows):
        diagnostics.append("streamed assistant output observed")
    if any(row.get("event_type") == "tool_call_result" for row in rows):
        diagnostics.append("tool results captured")
    if any(
        row.get("event_type") == "tool_call_result"
        and (
            "exit_code: 1" in str(row.get("payload", {}).get("output", ""))
            or "command not found" in str(row.get("payload", {}).get("output", "")).lower()
        )
        for row in rows
    ):
        diagnostics.append("failed tool execution captured")
    if any(row.get("event_type") == "exec_approval_request" for row in rows):
        diagnostics.append("approval path observed")
    if any(row.get("event_type") == "request_user_input" for row in rows):
        diagnostics.append("request-user-input path observed")
    return diagnostics or ["no special runtime diagnostics"]
