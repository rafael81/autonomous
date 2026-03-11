"""User-facing CLI application flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .baseline import compare_capture_against_baselines
from .io import read_jsonl
from .memory import MemoryTurn, append_session_memory, load_session_memory
from .orchestration import decide_orchestration, write_approval_artifact, write_request_user_input_artifact
from .postprocess import codexify_message
from .roma_runtime import run_roma_chat
from .strategy import build_steered_prompt, choose_strategy
from .workflow import ObservationRunResult, observe_prompt


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
        strategy = choose_strategy(prompt)
        result = run_roma_chat(
            prompt=prompt,
            history=memory_turns,
            captures_dir=captures_dir,
            cwd=cwd,
            instructions=build_steered_prompt(prompt, strategy),
            enable_tools=strategy.strategy_id == "tool_oriented",
        )
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
        return ChatRunSummary(
            final_message=final_message,
            strategy_id=strategy.strategy_id,
            baseline_example_id=strategy.baseline_example_id,
            attempted_strategies=[strategy.strategy_id],
            orchestration_summary=orchestration.policy_summary,
            session_dir=result.session_dir,
            normalized_path=result.normalized_path,
            promoted_example_dir=None,
            baseline_matches=len([item for item in comparison_results if item.matches]),
            baseline_total=len(comparison_results),
            comparison_summary_path=None,
            request_user_input_path=request_user_input_path,
            adaptive_notes="Roma runtime bridge executed with strategy steering.",
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
