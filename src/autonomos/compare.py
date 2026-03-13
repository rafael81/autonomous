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


IGNORED_EVENT_TYPES = {"tool_profile", "assistant_message_delta", "user_input"}
INSPECTION_TOOL_NAMES = {"shell", "bash", "list_dir", "read_file", "grep_text", "glob_paths", "search_files"}


def _core_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("event_type") not in IGNORED_EVENT_TYPES]


def _tool_family(tool_name: str) -> str:
    if tool_name in INSPECTION_TOOL_NAMES:
        return "inspection"
    return tool_name


def _inspection_like(events: list[dict]) -> bool:
    tool_names = [
        event.get("payload", {}).get("tool_name", "")
        for event in events
        if event["event_type"] in {"tool_call_request", "tool_call_result", "tool_call_error"}
    ]
    return bool(tool_names) and all(_tool_family(name) == "inspection" for name in tool_names)


def _tool_signature(events: list[dict], *, relax_inspection: bool = False) -> list[str]:
    signatures: list[str] = []
    for event in events:
        if event["event_type"] in {"tool_call_request", "tool_call_result", "tool_call_error", "request_user_input"}:
            tool_name = event["payload"].get("tool_name", event["event_type"])
            if relax_inspection:
                tool_name = _tool_family(tool_name)
            signatures.append(f"{event['event_type']}:{tool_name}")
    return signatures


def _event_shape(event: dict, *, relax_inspection: bool = False) -> str:
    payload = event.get("payload", {})
    event_type = event["event_type"]
    if event_type in {"tool_call_request", "tool_call_result", "tool_call_error"}:
        tool_name = payload.get("tool_name", "")
        if relax_inspection:
            tool_name = _tool_family(tool_name)
        return f"{event_type}:{tool_name}"
    if event_type in {"assistant_message", "assistant_message_delta"}:
        return f"{event_type}:{'text' if bool(payload.get('text')) else 'empty'}"
    if event_type == "request_user_input":
        questions = payload.get("questions", [])
        if isinstance(questions, int):
            question_count = questions
        elif isinstance(questions, list):
            question_count = len(questions)
        else:
            question_count = 0
        return f"{event_type}:{question_count}"
    if event_type == "exec_approval_request":
        return f"{event_type}:{'present' if payload else 'empty'}"
    return event_type


def _paired_tool_counts(events: list[dict], *, relax_inspection: bool = False) -> Counter:
    pairs: Counter = Counter()
    for event in events:
        if event["event_type"] in {"tool_call_request", "tool_call_result"}:
            tool_name = event.get("payload", {}).get("tool_name", "")
            if relax_inspection:
                tool_name = _tool_family(tool_name)
            pairs[(event["event_type"], tool_name)] += 1
    return pairs


def _phase_sequence(events: list[dict], *, relax_inspection: bool = False) -> list[str]:
    phases: list[str] = []
    for event in events:
        event_type = event["event_type"]
        if relax_inspection and event_type in {"tool_call_request", "tool_call_result", "tool_call_error"}:
            phase = "inspection_loop"
        else:
            phase = event_type
        if not phases or phases[-1] != phase:
            phases.append(phase)
    return phases


def compare_normalized_sequences(expected: list[dict], actual: list[dict]) -> ComparisonResult:
    details: list[str] = []
    expected = _core_events(expected)
    actual = _core_events(actual)
    relax_inspection = _inspection_like(expected) and _inspection_like(actual)
    expected_types = [event["event_type"] for event in expected]
    actual_types = [event["event_type"] for event in actual]
    expected_shapes = [_event_shape(event, relax_inspection=relax_inspection) for event in expected]
    actual_shapes = [_event_shape(event, relax_inspection=relax_inspection) for event in actual]

    if relax_inspection:
        expected_phases = _phase_sequence(expected, relax_inspection=True)
        actual_phases = _phase_sequence(actual, relax_inspection=True)
        if expected_phases != actual_phases:
            details.append(f"inspection phase sequence differs: expected={expected_phases} actual={actual_phases}")
    elif expected_types != actual_types:
        details.append(f"event type sequence differs: expected={expected_types} actual={actual_types}")
    if not relax_inspection and expected_shapes != actual_shapes:
        details.append(f"event shape sequence differs: expected={expected_shapes} actual={actual_shapes}")

    expected_tools = _tool_signature(expected, relax_inspection=relax_inspection)
    actual_tools = _tool_signature(actual, relax_inspection=relax_inspection)
    if not relax_inspection and expected_tools != actual_tools:
        details.append(f"tool orchestration differs: expected={expected_tools} actual={actual_tools}")

    if not relax_inspection:
        expected_counts = Counter(expected_types)
        actual_counts = Counter(actual_types)
        if expected_counts != actual_counts:
            details.append(f"event counts differ: expected={dict(expected_counts)} actual={dict(actual_counts)}")

        expected_tool_pairs = _paired_tool_counts(expected, relax_inspection=relax_inspection)
        actual_tool_pairs = _paired_tool_counts(actual, relax_inspection=relax_inspection)
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
