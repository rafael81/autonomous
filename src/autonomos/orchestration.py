"""Codex-like orchestration policy and attempt evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .baseline import BaselineComparison
from .strategy import StrategyDecision


@dataclass(frozen=True)
class OrchestrationDecision:
    requires_approval: bool
    should_request_user_input: bool
    should_retry: bool
    retry_reason: str | None
    policy_summary: str


def write_request_user_input_artifact(*, session_dir: Path, prompt: str) -> Path:
    payload = {
        "questions": [
            {
                "id": "direction",
                "header": "Direction",
                "question": "Which direction should the run prioritize?",
                "options": [
                    {"label": "Speed", "description": "Prefer the fastest path to an answer."},
                    {"label": "Accuracy", "description": "Prefer extra checking and evidence."},
                    {"label": "Conservative", "description": "Avoid risky tool use and keep the answer narrow."},
                ],
            }
        ],
        "prompt": prompt,
    }
    path = session_dir / "request-user-input.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_request_user_input_response(
    *,
    request_path: Path,
    selected_option: str,
    notes: str = "",
) -> Path:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    response = {
        "request_path": str(request_path),
        "answers": [
            {
                "question_id": request["questions"][0]["id"],
                "selected_option": selected_option,
                "notes": notes,
            }
        ],
    }
    response_path = request_path.with_name("request-user-input-response.json")
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return response_path


def render_request_user_input_response(response_path: Path | None) -> str:
    if response_path is None or not response_path.exists():
        return ""
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    answers = payload.get("answers", [])
    if not answers:
        return ""
    rendered = ["User input answers:"]
    for answer in answers:
        rendered.append(
            f"- {answer.get('question_id')}: option={answer.get('selected_option')} notes={answer.get('notes', '')}".rstrip()
        )
    return "\n".join(rendered) + "\n\n"


def build_retry_appendix(retry_reason: str | None) -> str:
    if not retry_reason:
        return ""
    return (
        "\n\nRetry guidance:\n"
        f"- Previous attempt issue: {retry_reason}\n"
        "- On this retry, reduce unnecessary divergence from the baseline event structure.\n"
        "- Prefer the smallest tool footprint that can still answer correctly.\n"
    )


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
