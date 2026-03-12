"""Structural comparison for normalized observation traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonResult:
    matches: bool
    summary: str
    details: list[str]
    score: int


def _tool_signature(events: list[dict]) -> list[str]:
    signatures: list[str] = []
    for event in events:
        if event["event_type"] in {"tool_call_request", "tool_call_result", "tool_call_error", "request_user_input"}:
            tool_name = event["payload"].get("tool_name", event["event_type"])
            signatures.append(f"{event['event_type']}:{tool_name}")
    return signatures


def _event_shape(event: dict) -> str:
    payload = event.get("payload", {})
    event_type = event["event_type"]
    if event_type in {"tool_call_request", "tool_call_result", "tool_call_error"}:
        return f"{event_type}:{payload.get('tool_name', '')}"
    if event_type in {"assistant_message", "assistant_message_delta"}:
        return f"{event_type}:{'text' if bool(payload.get('text')) else 'empty'}"
    if event_type == "request_user_input":
        question_count = len(payload.get("questions", []))
        return f"{event_type}:{question_count}"
    if event_type == "exec_approval_request":
        return f"{event_type}:{'present' if payload else 'empty'}"
    return event_type


def _paired_tool_counts(events: list[dict]) -> Counter:
    pairs: Counter = Counter()
    for event in events:
        if event["event_type"] in {"tool_call_request", "tool_call_result"}:
            tool_name = event.get("payload", {}).get("tool_name", "")
            pairs[(event["event_type"], tool_name)] += 1
    return pairs


def compare_normalized_sequences(expected: list[dict], actual: list[dict]) -> ComparisonResult:
    details: list[str] = []
    expected_types = [event["event_type"] for event in expected]
    actual_types = [event["event_type"] for event in actual]
    expected_shapes = [_event_shape(event) for event in expected]
    actual_shapes = [_event_shape(event) for event in actual]

    if expected_types != actual_types:
        details.append(f"event type sequence differs: expected={expected_types} actual={actual_types}")
    if expected_shapes != actual_shapes:
        details.append(f"event shape sequence differs: expected={expected_shapes} actual={actual_shapes}")

    expected_tools = _tool_signature(expected)
    actual_tools = _tool_signature(actual)
    if expected_tools != actual_tools:
        details.append(f"tool orchestration differs: expected={expected_tools} actual={actual_tools}")

    expected_counts = Counter(expected_types)
    actual_counts = Counter(actual_types)
    if expected_counts != actual_counts:
        details.append(f"event counts differ: expected={dict(expected_counts)} actual={dict(actual_counts)}")

    expected_tool_pairs = _paired_tool_counts(expected)
    actual_tool_pairs = _paired_tool_counts(actual)
    if expected_tool_pairs != actual_tool_pairs:
        details.append(
            f"tool request/result counts differ: expected={dict(expected_tool_pairs)} actual={dict(actual_tool_pairs)}"
        )

    expected_final = next((event["payload"].get("text") for event in reversed(expected) if event["event_type"] == "assistant_message"), None)
    actual_final = next((event["payload"].get("text") for event in reversed(actual) if event["event_type"] == "assistant_message"), None)
    if bool(expected_final) != bool(actual_final):
        details.append("final assistant message presence differs")

    matches = not details
    summary = "matched structurally" if matches else "structural differences found"
    return ComparisonResult(matches=matches, summary=summary, details=details, score=len(details))
