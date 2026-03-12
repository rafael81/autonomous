"""Generalized orchestration policies for prompt routing and repo inspection."""

from __future__ import annotations

from dataclasses import dataclass

from .io import read_jsonl
from .strategy import StrategyDecision


@dataclass(frozen=True)
class PromptPolicy:
    prompt_mode: str
    tool_budget: int
    max_repeated_tool_calls: int
    preferred_roots: tuple[str, ...]
    excluded_roots: tuple[str, ...]
    stop_after_evidence: int
    preferred_tools: tuple[str, ...]
    fallback_tool: str


DEFAULT_POLICY = PromptPolicy(
    prompt_mode="general",
    tool_budget=6,
    max_repeated_tool_calls=2,
    preferred_roots=("src", "tests", "README.md", "pyproject.toml"),
    excluded_roots=(".git", ".venv", "node_modules", "captures", "examples_live", ".autonomos"),
    stop_after_evidence=2,
    preferred_tools=("read_file", "grep_text", "search_files", "glob_paths", "list_dir"),
    fallback_tool="bash",
)


def infer_prompt_policy(prompt: str, strategy: StrategyDecision | None = None) -> PromptPolicy:
    text = prompt.lower()
    review_prompt = any(
        token in text
        for token in (
            "review",
            "code review",
            "review this change",
            "review current changes",
            "리뷰",
        )
    )
    structure_prompt = any(
        token in text
        for token in (
            "project structure",
            "repository structure",
            "현재 프로젝트 구조 분석",
            "프로젝트 구조 분석",
            "프로젝트 구조",
            "structure",
        )
    )
    inspection_prompt = any(
        token in text
        for token in (
            "repository",
            "repo",
            "project analysis",
            "analyze this project",
            "analyze my project",
            "현재 내 프로젝트 분석",
            "현재 프로젝트 분석",
            "프로젝트 분석",
            "project structure",
            "프로젝트 구조",
            "structure",
            "directory",
            "folder",
            "file",
            "read",
            "inspect",
            "check",
            "find",
            "search",
        )
    ) or (strategy is not None and strategy.strategy_id == "tool_oriented")
    verification_prompt = any(token in text for token in ("test", "verify", "pytest", "check"))

    if review_prompt:
        return PromptPolicy(
            prompt_mode="code_review",
            tool_budget=8,
            max_repeated_tool_calls=2,
            preferred_roots=("src", "tests", "README.md", "pyproject.toml"),
            excluded_roots=DEFAULT_POLICY.excluded_roots,
            stop_after_evidence=3,
            preferred_tools=("bash", "glob_paths", "grep_text", "read_file"),
            fallback_tool="bash",
        )
    if structure_prompt:
        return PromptPolicy(
            prompt_mode="structure_inspection",
            tool_budget=5,
            max_repeated_tool_calls=2,
            preferred_roots=("src", "tests", "README.md", "pyproject.toml"),
            excluded_roots=DEFAULT_POLICY.excluded_roots,
            stop_after_evidence=2,
            preferred_tools=("list_dir", "glob_paths", "read_file", "search_files", "grep_text"),
            fallback_tool="bash",
        )
    if inspection_prompt and verification_prompt:
        return PromptPolicy(
            prompt_mode="inspection_and_verification",
            tool_budget=8,
            max_repeated_tool_calls=2,
            preferred_roots=("src", "tests", "README.md", "pyproject.toml"),
            excluded_roots=DEFAULT_POLICY.excluded_roots,
            stop_after_evidence=3,
            preferred_tools=("list_dir", "glob_paths", "grep_text", "read_file", "bash"),
            fallback_tool="bash",
        )
    if inspection_prompt:
        return PromptPolicy(
            prompt_mode="repository_inspection",
            tool_budget=5,
            max_repeated_tool_calls=2,
            preferred_roots=("src", "tests", "README.md", "pyproject.toml"),
            excluded_roots=DEFAULT_POLICY.excluded_roots,
            stop_after_evidence=2,
            preferred_tools=("list_dir", "read_file", "search_files", "grep_text", "glob_paths"),
            fallback_tool="bash",
        )
    if verification_prompt:
        return PromptPolicy(
            prompt_mode="verification",
            tool_budget=6,
            max_repeated_tool_calls=2,
            preferred_roots=("tests", "src", "pyproject.toml", "README.md"),
            excluded_roots=DEFAULT_POLICY.excluded_roots,
            stop_after_evidence=2,
            preferred_tools=("glob_paths", "grep_text", "read_file", "bash"),
            fallback_tool="bash",
        )
    return DEFAULT_POLICY
def rank_roma_attempt(prompt: str, attempt) -> tuple[int, int, int, int, int, str]:
    policy = infer_prompt_policy(prompt, getattr(attempt, "strategy", None))
    rows = read_jsonl(attempt.result.normalized_path) if attempt.result.normalized_path.exists() else []
    tool_rows = [row for row in rows if row.get("event_type") in {"tool_call_request", "tool_call_result"}]
    tool_names = [row.get("payload", {}).get("tool_name", "") for row in tool_rows]
    final_message = extract_attempt_message(rows)
    inspection_without_tools_penalty = 0
    substantive_evidence_penalty = 0
    planning_penalty = 0

    preferred_tool_penalty = 0
    if policy.prompt_mode in {"structure_inspection", "repository_inspection", "inspection_and_verification"} and not tool_rows:
        inspection_without_tools_penalty = 1
    if policy.prompt_mode.startswith("repository_") or policy.prompt_mode == "inspection_and_verification":
        if not any(name in policy.preferred_tools for name in tool_names):
            preferred_tool_penalty = 1
    if policy.prompt_mode == "structure_inspection":
        if not any(name in {"list_dir", "glob_paths", "read_file"} for name in tool_names):
            substantive_evidence_penalty = 1
    elif policy.prompt_mode == "repository_inspection":
        if not tool_rows:
            substantive_evidence_penalty = 1
        lowered = final_message.lower()
        if any(token in lowered for token in ("보류", "실행 계획", "붙여주시면", "실행해야 할", "분석 계획")):
            planning_penalty = 1
    elif policy.prompt_mode == "code_review":
        lowered = final_message.lower()
        if not tool_rows:
            substantive_evidence_penalty = 1
        if "bash" not in tool_names:
            preferred_tool_penalty = 1
        if "prioritized" not in lowered and "risk" not in lowered and "finding" not in lowered:
            substantive_evidence_penalty = 1

    access_fallback_penalty = 1 if looks_like_access_fallback(final_message) else 0
    empty_fallback_penalty = 1 if is_empty_runtime_fallback(final_message) else 0
    over_budget_penalty = 1 if len(tool_rows) > policy.tool_budget * 2 else 0
    comparison_score = getattr(attempt, "comparison_score", 10_000)
    comparison_matches = getattr(attempt, "comparison_matches", 0)
    near_golden_bonus = 0 if comparison_matches > 0 and comparison_score <= 1 else 1

    return (
        comparison_matches == 0,
        near_golden_bonus,
        inspection_without_tools_penalty,
        access_fallback_penalty,
        empty_fallback_penalty,
        planning_penalty,
        substantive_evidence_penalty,
        preferred_tool_penalty,
        over_budget_penalty,
        comparison_score,
        getattr(attempt.strategy, "strategy_id", ""),
    )


def extract_attempt_message(rows: list[dict]) -> str:
    for row in reversed(rows):
        if row.get("event_type") == "assistant_message":
            text = row.get("payload", {}).get("text", "") or ""
            if is_empty_runtime_fallback(text):
                synthesized = _synthesize_tool_result_summary(rows)
                return synthesized or text
            return text
    return ""


def _synthesize_tool_result_summary(rows: list[dict]) -> str | None:
    tool_results = [row for row in rows if row.get("event_type") == "tool_call_result"]
    if not tool_results:
        return None
    parts: list[str] = []
    for row in tool_results[:3]:
        tool_name = row.get("payload", {}).get("tool_name", "tool")
        output = str(row.get("payload", {}).get("output", "")).strip()
        if not output:
            continue
        preview = "; ".join(output.splitlines()[:3])
        parts.append(f"{tool_name}: {preview}")
    if not parts:
        return None
    return "Observed via tools. " + " | ".join(parts)


def looks_like_access_fallback(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "you can run",
            "you can use",
            "execute the command",
            "cannot access",
            "can't access",
            "직접 접근",
        )
    )


def is_empty_runtime_fallback(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {
        "",
        "요청을 처리했지만 텍스트 응답이 없습니다.",
        "the request completed but produced no text response.",
    }
