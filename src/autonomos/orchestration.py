"""Codex-like orchestration policy and attempt evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from .baseline import BaselineComparison
from .strategy import StrategyDecision


@dataclass(frozen=True)
class OrchestrationDecision:
    requires_approval: bool
    should_request_user_input: bool
    should_retry: bool
    retry_reason: str | None
    policy_summary: str


def decide_orchestration(
    *,
    strategy: StrategyDecision,
    comparison_results: list[BaselineComparison],
    has_normalized_output: bool,
    prompt: str,
) -> OrchestrationDecision:
    text = prompt.lower()
    requires_approval = strategy.sandbox_mode != "read-only" and not strategy.prefer_full_auto
    should_request_user_input = (
        "choose" in text
        or "which" in text
        or "pick" in text
        or strategy.baseline_example_id == "example-05-request-user-input"
    )
    matched = any(item.matches for item in comparison_results)
    best_score = min((item.score for item in comparison_results), default=10_000)
    should_retry = (not has_normalized_output) or (not matched and best_score >= 2)
    retry_reason = None
    if not has_normalized_output:
        retry_reason = "missing normalized output"
    elif not matched and best_score >= 2:
        retry_reason = "baseline mismatch remains high"

    summary_bits = [
        f"approval={'yes' if requires_approval else 'no'}",
        f"request_user_input={'yes' if should_request_user_input else 'no'}",
        f"retry={'yes' if should_retry else 'no'}",
    ]
    return OrchestrationDecision(
        requires_approval=requires_approval,
        should_request_user_input=should_request_user_input,
        should_retry=should_retry,
        retry_reason=retry_reason,
        policy_summary=", ".join(summary_bits),
    )
