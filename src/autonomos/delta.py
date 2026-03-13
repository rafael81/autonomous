"""Structured drift analysis between normalized traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .compare import IGNORED_EVENT_TYPES, INSPECTION_TOOL_NAMES


@dataclass(frozen=True)
class DriftCategory:
    name: str
    details: list[str]


@dataclass(frozen=True)
class DriftAnalysis:
    summary: str
    primary_causes: list[str]
    categories: list[DriftCategory]


def analyze_trace_drift(expected: list[dict], actual: list[dict]) -> DriftAnalysis:
    expected_core = _core_events(expected)
    actual_core = _core_events(actual)
    categories: list[DriftCategory] = []

    strategy_details = _strategy_drift(expected_core, actual_core)
    if strategy_details:
        categories.append(DriftCategory(name="strategy_selection", details=strategy_details))

    preamble_details = _preamble_drift(expected_core, actual_core)
    if preamble_details:
        categories.append(DriftCategory(name="preamble_shape", details=preamble_details))

    tool_routing_details = _tool_routing_drift(expected_core, actual_core)
    if tool_routing_details:
        categories.append(DriftCategory(name="tool_routing", details=tool_routing_details))

    tool_count_details = _tool_count_drift(expected_core, actual_core)
    if tool_count_details:
        categories.append(DriftCategory(name="tool_count", details=tool_count_details))

    result_shape_details = _result_shape_drift(expected_core, actual_core)
    if result_shape_details:
        categories.append(DriftCategory(name="result_shape", details=result_shape_details))

    retry_details = _retry_drift(expected_core, actual_core)
    if retry_details:
        categories.append(DriftCategory(name="retry_behavior", details=retry_details))

    artifact_details = _artifact_drift(expected_core, actual_core)
    if artifact_details:
        categories.append(DriftCategory(name="user_input_artifacts", details=artifact_details))

    final_format_details = _final_formatting_drift(expected_core, actual_core)
    if final_format_details:
        categories.append(DriftCategory(name="final_answer_formatting", details=final_format_details))

    if not categories:
        return DriftAnalysis(
            summary="No structured drift detected.",
            primary_causes=[],
            categories=[],
        )

    primary_causes = [category.name for category in categories[:3]]
    summary = "; ".join(f"{category.name}: {_summarize_detail(category.name, category.details[0])}" for category in categories[:3])
    return DriftAnalysis(summary=summary, primary_causes=primary_causes, categories=categories)


def _core_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("event_type") not in IGNORED_EVENT_TYPES]


def _tool_request_names(events: list[dict]) -> list[str]:
    return [
        event.get("payload", {}).get("tool_name", "")
        for event in events
        if event.get("event_type") == "tool_call_request"
    ]


def _assistant_messages(events: list[dict]) -> list[str]:
    return [
        str(event.get("payload", {}).get("text", "") or "")
        for event in events
        if event.get("event_type") == "assistant_message"
    ]


def _first_preamble_text(events: list[dict]) -> str:
    first_tool_index = next(
        (index for index, event in enumerate(events) if event.get("event_type") == "tool_call_request"),
        None,
    )
    for index, event in enumerate(events):
        if event.get("event_type") != "assistant_message":
            continue
        if first_tool_index is None or index < first_tool_index:
            return str(event.get("payload", {}).get("text", "") or "")
    return ""


def _strategy_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_has_tools = any(event.get("event_type") == "tool_call_request" for event in expected)
    actual_has_tools = any(event.get("event_type") == "tool_call_request" for event in actual)
    if expected_has_tools != actual_has_tools:
        return [f"expected tool usage={expected_has_tools} actual tool usage={actual_has_tools}"]
    return []


def _preamble_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_preamble = _first_preamble_text(expected)
    actual_preamble = _first_preamble_text(actual)
    expected_present = bool(expected_preamble.strip())
    actual_present = bool(actual_preamble.strip())
    if expected_present != actual_present:
        return [f"expected preamble present={expected_present} actual={actual_present}"]
    if expected_present and actual_present:
        expected_len = len(expected_preamble.split())
        actual_len = len(actual_preamble.split())
        if abs(expected_len - actual_len) >= 8:
            return [f"expected preamble length~{expected_len} actual~{actual_len} words"]
    return []


def _tool_routing_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_names = _tool_request_names(expected)
    actual_names = _tool_request_names(actual)
    if expected_names != actual_names:
        return [f"expected tool order={expected_names} actual={actual_names}"]
    return []


def _tool_count_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_counts = Counter(_tool_request_names(expected))
    actual_counts = Counter(_tool_request_names(actual))
    if expected_counts != actual_counts:
        return [f"expected tool counts={dict(expected_counts)} actual={dict(actual_counts)}"]
    return []


def _result_shape_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_tool_results = len([event for event in expected if event.get("event_type") == "tool_call_result"])
    actual_tool_results = len([event for event in actual if event.get("event_type") == "tool_call_result"])
    expected_final = bool(_assistant_messages(expected))
    actual_final = bool(_assistant_messages(actual))
    details: list[str] = []
    if expected_tool_results != actual_tool_results:
        details.append(f"expected tool results={expected_tool_results} actual={actual_tool_results}")
    if expected_final != actual_final:
        details.append(f"expected final assistant message={expected_final} actual={actual_final}")
    return details


def _retry_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_counts = Counter(event.get("event_type") for event in expected)
    actual_counts = Counter(event.get("event_type") for event in actual)
    details: list[str] = []
    if expected_counts.get("task_started", 0) != actual_counts.get("task_started", 0):
        details.append(
            f"expected task_started={expected_counts.get('task_started', 0)} actual={actual_counts.get('task_started', 0)}"
        )
    if expected_counts.get("assistant_message", 0) != actual_counts.get("assistant_message", 0):
        details.append(
            f"expected assistant_message count={expected_counts.get('assistant_message', 0)} actual={actual_counts.get('assistant_message', 0)}"
        )
    return details


def _artifact_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    tracked_types = ("request_user_input", "exec_approval_request")
    details: list[str] = []
    for event_type in tracked_types:
        expected_count = len([event for event in expected if event.get("event_type") == event_type])
        actual_count = len([event for event in actual if event.get("event_type") == event_type])
        if expected_count != actual_count:
            details.append(f"expected {event_type}={expected_count} actual={actual_count}")
    return details


def _final_formatting_drift(expected: list[dict], actual: list[dict]) -> list[str]:
    expected_messages = _assistant_messages(expected)
    actual_messages = _assistant_messages(actual)
    if not expected_messages or not actual_messages:
        return []
    expected_final = expected_messages[-1]
    actual_final = actual_messages[-1]
    expected_lines = len(expected_final.splitlines())
    actual_lines = len(actual_final.splitlines())
    details: list[str] = []
    if abs(expected_lines - actual_lines) >= 2:
        details.append(f"expected final line_count={expected_lines} actual={actual_lines}")
    expected_has_bullets = "- " in expected_final or "* " in expected_final
    actual_has_bullets = "- " in actual_final or "* " in actual_final
    if expected_has_bullets != actual_has_bullets:
        details.append(f"expected bullet_style={expected_has_bullets} actual={actual_has_bullets}")
    expected_has_fence = "```" in expected_final
    actual_has_fence = "```" in actual_final
    if expected_has_fence != actual_has_fence:
        details.append(f"expected code_fence={expected_has_fence} actual={actual_has_fence}")
    return details


def format_drift_analysis(analysis: DriftAnalysis) -> list[str]:
    if not analysis.categories:
        return ["aligned"]
    lines = [analysis.summary]
    for category in analysis.categories:
        detail_text = "; ".join(_summarize_detail(category.name, detail) for detail in category.details) if category.details else "none"
        lines.append(f"- {category.name}: {detail_text}")
    return lines


def _summarize_detail(category_name: str, detail: str) -> str:
    if category_name == "tool_routing" and "expected tool order=" in detail and "actual=" in detail:
        expected_names, actual_names = _extract_tool_name_lists(detail)
        if _is_inspection_family(expected_names, actual_names):
            return (
                "same inspection family, but the runtime used a shorter built-in tool path "
                f"({len(actual_names)} steps) than the Codex golden ({len(expected_names)} steps)"
            )
    if category_name == "tool_count" and "expected tool counts=" in detail and "actual=" in detail:
        expected_counts, actual_counts = _extract_count_maps(detail)
        if _is_inspection_count_family(expected_counts, actual_counts):
            return (
                "inspection evidence was gathered with fewer tool calls than the Codex golden "
                f"(actual={sum(actual_counts.values())}, golden={sum(expected_counts.values())})"
            )
    if category_name == "result_shape" and "expected tool results=" in detail and "actual=" in detail:
        numbers = [int(token) for token in detail.replace("=", " ").split() if token.isdigit()]
        if len(numbers) >= 2:
            return f"the runtime produced fewer evidence snapshots than the Codex golden (actual={numbers[1]}, golden={numbers[0]})"
    return detail


def _extract_tool_name_lists(detail: str) -> tuple[list[str], list[str]]:
    prefix = "expected tool order="
    middle = " actual="
    expected_raw = detail.split(prefix, 1)[1].split(middle, 1)[0]
    actual_raw = detail.split(middle, 1)[1]
    return (_parse_name_list(expected_raw), _parse_name_list(actual_raw))


def _parse_name_list(raw: str) -> list[str]:
    stripped = raw.strip().removeprefix("[").removesuffix("]")
    if not stripped:
        return []
    items: list[str] = []
    for part in stripped.split(","):
        token = part.strip().strip("'").strip('"')
        if token:
            items.append(token)
    return items


def _extract_count_maps(detail: str) -> tuple[dict[str, int], dict[str, int]]:
    prefix = "expected tool counts="
    middle = " actual="
    expected_raw = detail.split(prefix, 1)[1].split(middle, 1)[0]
    actual_raw = detail.split(middle, 1)[1]
    return (_parse_count_map(expected_raw), _parse_count_map(actual_raw))


def _parse_count_map(raw: str) -> dict[str, int]:
    stripped = raw.strip().removeprefix("{").removesuffix("}")
    if not stripped:
        return {}
    counts: dict[str, int] = {}
    for part in stripped.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        name = key.strip().strip("'").strip('"')
        try:
            counts[name] = int(value.strip())
        except ValueError:
            continue
    return counts


def _is_inspection_family(expected_names: list[str], actual_names: list[str]) -> bool:
    names = expected_names + actual_names
    return bool(names) and all(name in INSPECTION_TOOL_NAMES for name in names)


def _is_inspection_count_family(expected_counts: dict[str, int], actual_counts: dict[str, int]) -> bool:
    names = list(expected_counts) + list(actual_counts)
    return bool(names) and all(name in INSPECTION_TOOL_NAMES for name in names)
