"""Adaptive scoring summaries for repeated attempts."""

from __future__ import annotations

from dataclasses import dataclass

from .baseline import BaselineComparison


@dataclass(frozen=True)
class AdaptiveSummary:
    best_score: int | None
    improved: bool
    notes: str


def summarize_attempt_progress(attempt_scores: list[list[BaselineComparison]]) -> AdaptiveSummary:
    minima: list[int] = []
    for scores in attempt_scores:
        if not scores:
            continue
        minima.append(min(item.score for item in scores))

    if not minima:
        return AdaptiveSummary(best_score=None, improved=False, notes="No baseline scores were available.")

    improved = len(minima) > 1 and minima[-1] < minima[0]
    notes = f"Attempt scores: {minima}"
    if improved:
        notes += " (improved over retries)"
    return AdaptiveSummary(best_score=min(minima), improved=improved, notes=notes)
