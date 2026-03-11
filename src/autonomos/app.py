"""User-facing CLI application flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import read_jsonl
from .workflow import ObservationRunResult, observe_prompt


@dataclass(frozen=True)
class ChatRunSummary:
    final_message: str | None
    session_dir: Path
    normalized_path: Path | None
    promoted_example_dir: Path | None
    baseline_matches: int
    baseline_total: int
    comparison_summary_path: Path | None


def run_chat(
    *,
    prompt: str,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path,
    baselines_dir: Path,
) -> ChatRunSummary:
    outcome: ObservationRunResult = observe_prompt(
        prompt=prompt,
        profile=profile,
        cwd=cwd,
        captures_dir=captures_dir,
        promote_dir=promote_dir,
        baselines_dir=baselines_dir,
    )
    final_message = extract_final_message(outcome.capture.normalized_path)
    baseline_matches = len([item for item in outcome.comparison_results if item.matches])
    return ChatRunSummary(
        final_message=final_message,
        session_dir=outcome.capture.session_dir,
        normalized_path=outcome.capture.normalized_path,
        promoted_example_dir=outcome.promoted_example_dir,
        baseline_matches=baseline_matches,
        baseline_total=len(outcome.comparison_results),
        comparison_summary_path=outcome.summary_path,
    )


def extract_final_message(normalized_path: Path | None) -> str | None:
    if normalized_path is None or not normalized_path.exists():
        return None
    rows = read_jsonl(normalized_path)
    for row in reversed(rows):
        if row["event_type"] == "assistant_message":
            return row["payload"].get("text")
    return None
