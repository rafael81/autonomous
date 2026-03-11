"""Prompt strategy selection and Codex steering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDecision:
    strategy_id: str
    baseline_example_id: str
    rationale: str
    sandbox_mode: str
    reasoning_effort: str
    prefer_full_auto: bool


STRATEGY_LIBRARY: tuple[StrategyDecision, ...] = (
    StrategyDecision(
        strategy_id="simple_answer",
        baseline_example_id="example-01-simple-short",
        rationale="Short factual or direct request without tool hints.",
        sandbox_mode="read-only",
        reasoning_effort="low",
        prefer_full_auto=False,
    ),
    StrategyDecision(
        strategy_id="long_form",
        baseline_example_id="example-02-long-stream",
        rationale="Creative or long-form generation request.",
        sandbox_mode="read-only",
        reasoning_effort="medium",
        prefer_full_auto=False,
    ),
    StrategyDecision(
        strategy_id="tool_oriented",
        baseline_example_id="example-03-single-tool",
        rationale="Prompt suggests looking up, checking, reading, or running something.",
        sandbox_mode="workspace-write",
        reasoning_effort="medium",
        prefer_full_auto=True,
    ),
    StrategyDecision(
        strategy_id="planning",
        baseline_example_id="example-06-plan-only",
        rationale="Prompt explicitly asks for a plan, design, or non-mutating preparation.",
        sandbox_mode="read-only",
        reasoning_effort="medium",
        prefer_full_auto=False,
    ),
    StrategyDecision(
        strategy_id="safety_refusal",
        baseline_example_id="example-08-safety-refusal",
        rationale="Prompt appears unsafe or disallowed.",
        sandbox_mode="read-only",
        reasoning_effort="low",
        prefer_full_auto=False,
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
    if any(
        token in text
        for token in (
            "check",
            "inspect",
            "look up",
            "search",
            "read",
            "run",
            "test",
            "verify",
            "repository",
            "repo",
            "directory",
            "file",
            "folder",
            "structure",
            "analyze",
            "분석",
            "구조",
            "프로젝트",
            "저장소",
            "파일",
            "디렉터리",
            "읽",
            "검색",
            "확인",
        )
    ):
        return _by_id("tool_oriented")
    return _by_id("simple_answer")


def candidate_strategies(prompt: str, limit: int = 3) -> list[StrategyDecision]:
    text = prompt.lower()
    if any(
        token in text
        for token in (
            "project analysis",
            "analyze this project",
            "analyze my project",
            "현재 내 프로젝트 분석",
            "현재 프로젝트 분석",
            "프로젝트 분석",
            "현재 프로젝트 구조 분석",
            "프로젝트 구조 분석",
        )
    ):
        return [_by_id("tool_oriented")]

    primary = choose_strategy(prompt)
    ordered = [primary]

    if primary.strategy_id == "tool_oriented":
        ordered.extend([_by_id("planning"), _by_id("simple_answer")])
    elif primary.strategy_id == "planning":
        ordered.extend([_by_id("tool_oriented"), _by_id("simple_answer")])
    elif primary.strategy_id == "long_form":
        ordered.extend([_by_id("simple_answer")])
    elif primary.strategy_id == "simple_answer":
        ordered.extend([_by_id("tool_oriented")])

    deduped: list[StrategyDecision] = []
    seen: set[str] = set()
    for item in ordered:
        if item.strategy_id in seen:
            continue
        seen.add(item.strategy_id)
        deduped.append(item)
    return deduped[:limit]
def _by_id(strategy_id: str) -> StrategyDecision:
    for item in STRATEGY_LIBRARY:
        if item.strategy_id == strategy_id:
            return item
    raise KeyError(strategy_id)
