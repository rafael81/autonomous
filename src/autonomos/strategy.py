"""Prompt strategy selection and Codex steering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDecision:
    strategy_id: str
    baseline_example_id: str
    rationale: str
    steering_prompt: str
    sandbox_mode: str
    reasoning_effort: str
    prefer_full_auto: bool
    output_style: str


STRATEGY_LIBRARY: tuple[StrategyDecision, ...] = (
    StrategyDecision(
        strategy_id="simple_answer",
        baseline_example_id="example-01-simple-short",
        rationale="Short factual or direct request without tool hints.",
        steering_prompt=(
            "Respond directly and briefly. Avoid unnecessary planning. "
            "Do not call tools unless the user clearly asks for live verification or codebase inspection."
        ),
        sandbox_mode="read-only",
        reasoning_effort="low",
        prefer_full_auto=False,
        output_style="brief",
    ),
    StrategyDecision(
        strategy_id="long_form",
        baseline_example_id="example-02-long-stream",
        rationale="Creative or long-form generation request.",
        steering_prompt=(
            "Produce a polished long-form answer. Stream naturally in sections if helpful. "
            "Do not fabricate tool use."
        ),
        sandbox_mode="read-only",
        reasoning_effort="medium",
        prefer_full_auto=False,
        output_style="long",
    ),
    StrategyDecision(
        strategy_id="tool_oriented",
        baseline_example_id="example-03-single-tool",
        rationale="Prompt suggests looking up, checking, reading, or running something.",
        steering_prompt=(
            "Inspect the environment first, then answer from observed evidence. "
            "Use the minimum necessary tools and summarize findings clearly."
        ),
        sandbox_mode="workspace-write",
        reasoning_effort="medium",
        prefer_full_auto=True,
        output_style="evidence_first",
    ),
    StrategyDecision(
        strategy_id="planning",
        baseline_example_id="example-06-plan-only",
        rationale="Prompt explicitly asks for a plan, design, or non-mutating preparation.",
        steering_prompt=(
            "Focus on a decision-complete implementation plan. "
            "Do not mutate files unless the user explicitly asks to implement."
        ),
        sandbox_mode="read-only",
        reasoning_effort="medium",
        prefer_full_auto=False,
        output_style="structured_plan",
    ),
    StrategyDecision(
        strategy_id="safety_refusal",
        baseline_example_id="example-08-safety-refusal",
        rationale="Prompt appears unsafe or disallowed.",
        steering_prompt=(
            "Refuse unsafe assistance briefly and redirect to a safe alternative."
        ),
        sandbox_mode="read-only",
        reasoning_effort="low",
        prefer_full_auto=False,
        output_style="brief_refusal",
    ),
)


def choose_strategy(prompt: str) -> StrategyDecision:
    text = prompt.lower()

    if any(token in text for token in ("unsafe", "malware", "exploit", "steal", "bypass")):
        return _by_id("safety_refusal")
    if any(token in text for token in ("plan", "design", "spec", "approach", "strategy")):
        return _by_id("planning")
    if any(token in text for token in ("write a story", "write an essay", "long", "story", "narrative")):
        return _by_id("long_form")
    if any(token in text for token in ("check", "inspect", "look up", "search", "read", "run", "test", "verify")):
        return _by_id("tool_oriented")
    return _by_id("simple_answer")


def build_steered_prompt(user_prompt: str, decision: StrategyDecision) -> str:
    return (
        "You are Autonomos, a Codex-aligned CLI assistant.\n"
        f"Preferred interaction archetype: {decision.strategy_id}.\n"
        f"Reference baseline: {decision.baseline_example_id}.\n"
        f"Output style: {decision.output_style}.\n"
        f"Reasoning effort: {decision.reasoning_effort}.\n"
        f"Execution guidance: {decision.steering_prompt}\n\n"
        "User request:\n"
        f"{user_prompt}"
    )


def _by_id(strategy_id: str) -> StrategyDecision:
    for item in STRATEGY_LIBRARY:
        if item.strategy_id == strategy_id:
            return item
    raise KeyError(strategy_id)
