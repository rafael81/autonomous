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
    inspection_prompt = any(
        token in text
        for token in (
            "repository",
            "repo",
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


def render_policy_guidance(policy: PromptPolicy) -> str:
    return (
        "General orchestration policy:\n"
        f"- prompt_mode: {policy.prompt_mode}\n"
        f"- tool_budget: {policy.tool_budget}\n"
        f"- max_repeated_tool_calls: {policy.max_repeated_tool_calls}\n"
        f"- preferred_roots: {', '.join(policy.preferred_roots)}\n"
        f"- excluded_roots: {', '.join(policy.excluded_roots)}\n"
        f"- stop_after_evidence: {policy.stop_after_evidence}\n"
        f"- preferred_tools: {', '.join(policy.preferred_tools)}\n"
        f"- fallback_tool: {policy.fallback_tool}\n"
        "- Start from higher-value evidence before broad exploration.\n"
        "- Stop once the available evidence is enough to answer reliably.\n"
        "- Avoid scanning generated or cached directories unless the user explicitly asks for them.\n"
    )


def rank_roma_attempt(prompt: str, attempt) -> tuple[int, int, int, int, int, str]:
    policy = infer_prompt_policy(prompt, getattr(attempt, "strategy", None))
    rows = read_jsonl(attempt.result.normalized_path) if attempt.result.normalized_path.exists() else []
    tool_rows = [row for row in rows if row.get("event_type") in {"tool_call_request", "tool_call_result"}]
    tool_names = [row.get("payload", {}).get("tool_name", "") for row in tool_rows]
    final_message = extract_attempt_message(rows)

    preferred_tool_penalty = 0
    if policy.prompt_mode.startswith("repository_") or policy.prompt_mode == "inspection_and_verification":
        if not any(name in policy.preferred_tools for name in tool_names):
            preferred_tool_penalty = 1

    access_fallback_penalty = 1 if looks_like_access_fallback(final_message) else 0
    empty_fallback_penalty = 1 if is_empty_runtime_fallback(final_message) else 0
    over_budget_penalty = 1 if len(tool_rows) > policy.tool_budget * 2 else 0
    comparison_score = getattr(attempt, "comparison_score", 10_000)
    comparison_matches = getattr(attempt, "comparison_matches", 0)

    return (
        comparison_matches == 0,
        access_fallback_penalty,
        empty_fallback_penalty,
        preferred_tool_penalty,
        over_budget_penalty,
        comparison_score,
        getattr(attempt.strategy, "strategy_id", ""),
    )


def extract_attempt_message(rows: list[dict]) -> str:
    for row in reversed(rows):
        if row.get("event_type") == "assistant_message":
            return row.get("payload", {}).get("text", "") or ""
    return ""


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
