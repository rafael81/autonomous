"""Prompt strategy selection and Codex steering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


GOLDENS_ROOT = Path("goldens")


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


def is_status_summary_prompt(prompt: str) -> bool:
    text = prompt.lower()
    if "codex" not in text and "autonomos" not in text and "cli" not in text:
        return False
    return any(
        token in text
        for token in (
            "score",
            "rating",
            "how close",
            "how good",
            "how much",
            "how far",
            "compared to",
            "vs codex",
            "completion",
            "parity",
            "current level",
            "status",
            "몇 점",
            "점수",
            "어느정도",
            "어느 정도",
            "비교",
            "수준",
            "완성도",
            "달성률",
        )
    )


def is_review_prompt(prompt: str) -> bool:
    text = prompt.lower()
    return any(token in text for token in ("review", "code review", "current changes", "diff", "리뷰", "findings"))


def is_request_user_input_prompt(prompt: str) -> bool:
    text = prompt.lower()
    return any(
        token in text
        for token in (
            "choose a direction first",
            "ask me to choose",
            "pick a direction first",
            "choose first",
            "choose a direction",
            "먼저 선택",
            "방향을 고르게",
            "선택하게",
        )
    )


def choose_strategy(prompt: str) -> StrategyDecision:
    text = prompt.lower()

    if is_review_prompt(prompt):
        return _by_id("tool_oriented")
    if is_request_user_input_prompt(prompt):
        return _by_id("planning")
    if is_status_summary_prompt(prompt):
        return _by_id("simple_answer")
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


def candidate_strategies(prompt: str, limit: int = 3, goldens_root: Path = GOLDENS_ROOT) -> list[StrategyDecision]:
    text = prompt.lower()
    if is_review_prompt(prompt):
        return [_by_id("tool_oriented")]
    if is_request_user_input_prompt(prompt):
        return [_by_id("planning")]
    if is_status_summary_prompt(prompt):
        return [_by_id("simple_answer")]
    if any(
        token in text
        for token in (
            "현재 내 프로젝트 분석",
            "현재 프로젝트 구조 분석",
            "프로젝트 구조 분석",
        )
    ):
        return [_by_id("tool_oriented")]

    primary = infer_golden_strategy_hint(prompt, goldens_root=goldens_root) or choose_strategy(prompt)
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


def infer_golden_strategy_hint(prompt: str, goldens_root: Path = GOLDENS_ROOT) -> StrategyDecision | None:
    if not goldens_root.exists():
        return None
    prompt_tokens = _tokenize(prompt)
    if not prompt_tokens:
        return None

    best_score = 0.0
    best_prompt = None
    for prompt_path in goldens_root.glob("*/prompt.txt"):
        golden_prompt = prompt_path.read_text(encoding="utf-8").strip()
        golden_tokens = _tokenize(golden_prompt)
        if not golden_tokens:
            continue
        overlap = len(prompt_tokens & golden_tokens)
        union = len(prompt_tokens | golden_tokens)
        score = overlap / union if union else 0.0
        if score > best_score:
            best_score = score
            best_prompt = golden_prompt

    if best_prompt is None or best_score < 0.55:
        return None
    return choose_strategy(best_prompt)


def _tokenize(text: str) -> set[str]:
    normalized = (
        text.lower()
        .replace(".", " ")
        .replace(",", " ")
        .replace(":", " ")
        .replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
        .replace("\n", " ")
    )
    return {token for token in normalized.split() if len(token) >= 2}


def _by_id(strategy_id: str) -> StrategyDecision:
    for item in STRATEGY_LIBRARY:
        if item.strategy_id == strategy_id:
            return item
    raise KeyError(strategy_id)
