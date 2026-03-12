"""Runtime verification helpers driven by golden prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app import ChatRunSummary, run_chat
from .baseline import build_golden_registry


@dataclass(frozen=True)
class VerificationResult:
    example_id: str
    prompt: str
    closest_match_example_id: str | None
    closest_match_score: int | None
    strategy_id: str
    final_message: str | None
    matched_expected_golden: bool


def verify_runtime_against_goldens(
    *,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path,
    baselines_dir: Path,
    memory_dir: Path,
    goldens_dir: Path,
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    comparison_root = goldens_dir if goldens_dir.exists() else baselines_dir
    for row in build_golden_registry(goldens_dir):
        example_id = str(row["example_id"])
        prompt = str(row["prompt"])
        summary: ChatRunSummary = run_chat(
            prompt=prompt,
            profile=profile,
            cwd=cwd,
            captures_dir=captures_dir / example_id,
            promote_dir=promote_dir / example_id,
            baselines_dir=comparison_root,
            memory_dir=memory_dir,
            session_id=f"verify-{example_id}",
        )
        results.append(
            VerificationResult(
                example_id=example_id,
                prompt=prompt,
                closest_match_example_id=summary.closest_match_example_id,
                closest_match_score=summary.closest_match_score,
                strategy_id=summary.strategy_id,
                final_message=summary.final_message,
                matched_expected_golden=(
                    summary.closest_match_example_id == example_id
                    and summary.closest_match_score == 0
                ),
            )
        )
    return results


def format_verification_results(results: list[VerificationResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        status = "MATCH" if result.matched_expected_golden else "DIFF"
        lines.append(
            f"{status} {result.example_id}: closest={result.closest_match_example_id or 'none'} "
            f"score={result.closest_match_score if result.closest_match_score is not None else '?'} "
            f"strategy={result.strategy_id}"
        )
    return lines
