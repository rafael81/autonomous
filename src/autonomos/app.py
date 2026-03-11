"""User-facing CLI application flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adaptive import AdaptiveSummary, summarize_attempt_progress
from .baseline import compare_capture_against_baselines, promote_capture_to_example
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
from .postprocess import codexify_message
from .reports import build_report
from .roma_runtime import RomaAttemptResult, run_roma_chat
from .strategy import build_steered_prompt, candidate_strategies, choose_strategy
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
) -> ChatRunSummary:
    memory_turns = load_session_memory(memory_dir, session_id)
    memory_path = None
    if profile == "roma_ws":
        attempts: list[RomaAttemptResult] = []
        retry_appendix = ""
        user_input_prefix = render_request_user_input_response(request_user_input_response_path)
        approval_prefix = render_approval_response(approval_response_path)
        memory_prefix = render_memory_context(memory_turns)
        for attempt_index, strategy in enumerate(candidate_strategies(prompt), start=1):
            steered_prompt = memory_prefix + approval_prefix + user_input_prefix + build_steered_prompt(prompt, strategy) + retry_appendix
            result = run_roma_chat(
                prompt=steered_prompt,
                history=memory_turns,
                captures_dir=captures_dir / f"attempt-{attempt_index}-{strategy.strategy_id}",
                cwd=cwd,
                instructions=memory_prefix + build_steered_prompt(prompt, strategy),
                enable_tools=strategy.strategy_id == "tool_oriented",
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
            attempts.append(
                RomaAttemptResult(
                    result=result,
                    strategy=strategy,
                    comparison_score=min((item.score for item in comparison_results), default=10_000),
                    comparison_matches=len([item for item in comparison_results if item.matches]),
                )
            )
            retry_appendix = build_retry_appendix(orchestration.retry_reason)
            if any(item.matches for item in comparison_results):
                break

        best_attempt = min(attempts, key=lambda item: _rank_roma_attempt(prompt, item))
        strategy = best_attempt.strategy
        result = best_attempt.result
        final_message = codexify_message(result.final_message)
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
                        f"adaptive={adaptive_summary.notes}"
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
    )


def extract_final_message(normalized_path: Path | None) -> str | None:
    if normalized_path is None or not normalized_path.exists():
        return None
    rows = read_jsonl(normalized_path)
    for row in reversed(rows):
        if row["event_type"] == "assistant_message":
            return row["payload"].get("text")
    return None


def _rank_roma_attempt(prompt: str, attempt: RomaAttemptResult) -> tuple[int, int, int, int, str]:
    prompt_lower = prompt.lower()
    inspection_prompt = any(
        token in prompt_lower
        for token in ("list", "read", "inspect", "check", "find", "search", "repository", "directory", "file")
    )
    rows = read_jsonl(attempt.result.normalized_path) if attempt.result.normalized_path.exists() else []
    tool_events = [row for row in rows if row.get("event_type") in {"tool_call_request", "tool_call_result"}]
    tool_bonus = 0 if (inspection_prompt and tool_events) else 1
    final_message = extract_final_message(attempt.result.normalized_path) or ""
    fallback_penalty = 1 if _looks_like_access_fallback(final_message) else 0
    return (
        attempt.comparison_matches == 0,
        fallback_penalty,
        tool_bonus,
        attempt.comparison_score,
        attempt.strategy.strategy_id,
    )


def _looks_like_access_fallback(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "cannot access",
            "can't access",
            "직접 접근",
            "결과를 붙여주시면",
            "you can run",
            "run the following commands",
        )
    )
