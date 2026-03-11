"""End-to-end observation workflow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .adaptive import AdaptiveSummary, summarize_attempt_progress
from .baseline import BaselineComparison, compare_capture_against_baselines, promote_capture_to_example
from .codex_exec import build_exec_command
from .live_capture import LiveCaptureResult, SavedCapturePaths, run_capture, save_capture_session
from .memory import MemoryTurn, render_memory_context
from .orchestration import (
    OrchestrationDecision,
    build_retry_appendix,
    decide_orchestration,
    render_request_user_input_response,
    write_request_user_input_artifact,
)
from .strategy import StrategyDecision, build_steered_prompt, candidate_strategies


@dataclass(frozen=True)
class ObservationRunResult:
    capture: SavedCapturePaths
    promoted_example_dir: Path | None
    comparison_results: list[BaselineComparison]
    summary_path: Path | None
    strategy: StrategyDecision
    attempted_strategies: list[str]
    orchestration: OrchestrationDecision
    request_user_input_path: Path | None
    adaptive_summary: AdaptiveSummary


@dataclass(frozen=True)
class AttemptResult:
    capture: SavedCapturePaths
    comparison_results: list[BaselineComparison]
    strategy: StrategyDecision
    orchestration: OrchestrationDecision


def observe_prompt(
    *,
    prompt: str,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path | None = None,
    baselines_dir: Path | None = None,
    example_id: str | None = None,
    memory_turns: list[MemoryTurn] | None = None,
    request_user_input_response_path: Path | None = None,
    runner=run_capture,
) -> ObservationRunResult:
    attempts: list[AttemptResult] = []
    strategies = candidate_strategies(prompt)
    retry_appendix = ""
    memory_prefix = render_memory_context(memory_turns or [])
    user_input_prefix = render_request_user_input_response(request_user_input_response_path)
    for attempt_index, strategy in enumerate(strategies, start=1):
        steered_prompt = memory_prefix + user_input_prefix + build_steered_prompt(prompt, strategy) + retry_appendix
        command = build_exec_command(prompt=steered_prompt, profile=profile, cwd=cwd, strategy=strategy)
        result: LiveCaptureResult = runner(command, cwd=cwd)
        saved = save_capture_session(
            result=result,
            prompt=prompt,
            output_root=captures_dir / f"attempt-{attempt_index}-{strategy.strategy_id}",
        )
        comparison_results: list[BaselineComparison] = []
        if baselines_dir and saved.normalized_path:
            comparison_results = compare_capture_against_baselines(
                normalized_path=saved.normalized_path,
                baselines_root=baselines_dir,
            )
        orchestration = decide_orchestration(
            strategy=strategy,
            comparison_results=comparison_results,
            has_normalized_output=saved.normalized_path is not None,
            prompt=prompt,
        )
        attempts.append(
            AttemptResult(
                capture=saved,
                comparison_results=comparison_results,
                strategy=strategy,
                orchestration=orchestration,
            )
        )
        retry_appendix = build_retry_appendix(orchestration.retry_reason)
        if any(item.matches for item in comparison_results):
            break

    best_attempt = select_best_attempt(attempts)
    strategy = best_attempt.strategy
    saved = best_attempt.capture
    comparison_results = best_attempt.comparison_results
    orchestration = best_attempt.orchestration
    request_user_input_path: Path | None = None
    if orchestration.should_request_user_input:
        request_user_input_path = write_request_user_input_artifact(session_dir=saved.session_dir, prompt=prompt)
    adaptive_summary = summarize_attempt_progress([attempt.comparison_results for attempt in attempts])

    promoted_example_dir: Path | None = None
    if promote_dir and saved.normalized_path:
        promoted_example_dir = promote_capture_to_example(
            capture_dir=saved.session_dir,
            output_root=promote_dir,
            example_id=example_id or slugify_prompt(prompt),
            prompt=prompt,
        )

    summary_path: Path | None = None
    if baselines_dir and saved.normalized_path:
        summary_path = saved.session_dir / "comparison-summary.md"
        summary_path.write_text(
            build_comparison_summary(
                prompt=prompt,
                strategy=strategy,
                orchestration=orchestration,
                comparison_results=comparison_results,
                promoted_example_dir=promoted_example_dir,
                attempted_strategies=[attempt.strategy.strategy_id for attempt in attempts],
                adaptive_summary=adaptive_summary,
            )
            + "\n",
            encoding="utf-8",
        )

    return ObservationRunResult(
        capture=saved,
        promoted_example_dir=promoted_example_dir,
        comparison_results=comparison_results,
        summary_path=summary_path,
        strategy=strategy,
        attempted_strategies=[attempt.strategy.strategy_id for attempt in attempts],
        orchestration=orchestration,
        request_user_input_path=request_user_input_path,
        adaptive_summary=adaptive_summary,
    )


def select_best_attempt(attempts: list[AttemptResult]) -> AttemptResult:
    if not attempts:
        raise ValueError("at least one attempt is required")

    def score_attempt(attempt: AttemptResult) -> tuple[int, int, int, int]:
        if not attempt.comparison_results:
            return (1, 10_000, 1, 10_000)
        best = min(item.score for item in attempt.comparison_results)
        match_bonus = 0 if any(item.matches for item in attempt.comparison_results) else 1
        retry_penalty = 1 if attempt.orchestration.should_retry else 0
        return (match_bonus, best, retry_penalty, len(attempt.comparison_results))

    return min(attempts, key=score_attempt)


def build_comparison_summary(
    *,
    prompt: str,
    strategy: StrategyDecision,
    orchestration: OrchestrationDecision,
    comparison_results: list[BaselineComparison],
    promoted_example_dir: Path | None,
    attempted_strategies: list[str],
    adaptive_summary: AdaptiveSummary,
) -> str:
    sorted_results = sorted(
        comparison_results,
        key=lambda item: (
            not item.matches,
            len(item.details),
            item.example_id,
        ),
    )
    lines = [
        "# Observation Summary",
        "",
        "## Prompt",
        prompt,
        "",
        "## Strategy",
        f"{strategy.strategy_id} -> {strategy.baseline_example_id}",
        "",
        "## Attempted Strategies",
        ", ".join(attempted_strategies) if attempted_strategies else "none",
        "",
        "## Orchestration Policy",
        orchestration.policy_summary,
        "",
        "## Adaptive Summary",
        adaptive_summary.notes,
        "",
        "## Promoted Example",
        str(promoted_example_dir) if promoted_example_dir else "none",
        "",
        "## Baseline Comparison",
    ]
    if not sorted_results:
        lines.append("No baseline comparison was run.")
    else:
        for item in sorted_results[:10]:
            status = "MATCH" if item.matches else "DIFF"
            lines.append(f"- {status} {item.example_id}: {item.summary}")
            if item.details:
                lines.append(f"  details: {item.details[0]}")
    return "\n".join(lines)


def slugify_prompt(prompt: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")
    return slug[:50] or "observed-prompt"
