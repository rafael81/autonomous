"""End-to-end observation workflow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .baseline import BaselineComparison, compare_capture_against_baselines, promote_capture_to_example
from .codex_exec import build_exec_command
from .live_capture import LiveCaptureResult, SavedCapturePaths, run_capture, save_capture_session
from .strategy import StrategyDecision, build_steered_prompt, choose_strategy


@dataclass(frozen=True)
class ObservationRunResult:
    capture: SavedCapturePaths
    promoted_example_dir: Path | None
    comparison_results: list[BaselineComparison]
    summary_path: Path | None
    strategy: StrategyDecision


def observe_prompt(
    *,
    prompt: str,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path | None = None,
    baselines_dir: Path | None = None,
    example_id: str | None = None,
    runner=run_capture,
) -> ObservationRunResult:
    strategy = choose_strategy(prompt)
    steered_prompt = build_steered_prompt(prompt, strategy)
    command = build_exec_command(prompt=steered_prompt, profile=profile, cwd=cwd, strategy=strategy)
    result: LiveCaptureResult = runner(command, cwd=cwd)
    saved = save_capture_session(result=result, prompt=prompt, output_root=captures_dir)

    promoted_example_dir: Path | None = None
    if promote_dir and saved.normalized_path:
        promoted_example_dir = promote_capture_to_example(
            capture_dir=saved.session_dir,
            output_root=promote_dir,
            example_id=example_id or slugify_prompt(prompt),
            prompt=prompt,
        )

    comparison_results: list[BaselineComparison] = []
    summary_path: Path | None = None
    if baselines_dir and saved.normalized_path:
        comparison_results = compare_capture_against_baselines(
            normalized_path=saved.normalized_path,
            baselines_root=baselines_dir,
        )
        summary_path = saved.session_dir / "comparison-summary.md"
        summary_path.write_text(
            build_comparison_summary(
                prompt=prompt,
                strategy=strategy,
                comparison_results=comparison_results,
                promoted_example_dir=promoted_example_dir,
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
    )


def build_comparison_summary(
    *,
    prompt: str,
    strategy: StrategyDecision,
    comparison_results: list[BaselineComparison],
    promoted_example_dir: Path | None,
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
