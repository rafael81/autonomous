"""User-facing CLI application flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import read_jsonl
from .memory import MemoryTurn, append_session_memory, load_session_memory
from .postprocess import codexify_message
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
) -> ChatRunSummary:
    memory_turns = load_session_memory(memory_dir, session_id)
    outcome: ObservationRunResult = observe_prompt(
        prompt=prompt,
        profile=profile,
        cwd=cwd,
        captures_dir=captures_dir,
        promote_dir=promote_dir,
        baselines_dir=baselines_dir,
        memory_turns=memory_turns,
    )
    final_message = codexify_message(extract_final_message(outcome.capture.normalized_path))
    baseline_matches = len([item for item in outcome.comparison_results if item.matches])
    memory_path = None
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
    )


def extract_final_message(normalized_path: Path | None) -> str | None:
    if normalized_path is None or not normalized_path.exists():
        return None
    rows = read_jsonl(normalized_path)
    for row in reversed(rows):
        if row["event_type"] == "assistant_message":
            return row["payload"].get("text")
    return None
