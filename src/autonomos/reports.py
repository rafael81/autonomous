"""Example report generation."""

from __future__ import annotations

from collections import Counter


def build_report(*, example_id: str, prompt: str, normalized_events: list[dict], notes: str = "") -> str:
    event_counts = Counter(event["event_type"] for event in normalized_events)
    timeline = []
    for index, event in enumerate(normalized_events[:12], start=1):
        summary = event["event_type"]
        if event["payload"].get("text"):
            summary += f": {event['payload']['text'][:80]}"
        elif event["payload"].get("delta"):
            summary += f": {event['payload']['delta']}"
        timeline.append(f"{index}. {event['ts']} {summary}")

    assistant_messages = [e["payload"].get("text", "") for e in normalized_events if e["event_type"] == "assistant_message"]
    tool_calls = [e for e in normalized_events if "tool" in e["event_type"]]

    return "\n".join(
        [
            f"# {example_id}",
            "",
            "## Input Prompt",
            prompt,
            "",
            "## Observation Summary",
            f"- total normalized events: {len(normalized_events)}",
            f"- event types: {dict(sorted(event_counts.items()))}",
            "",
            "## Event Timeline",
            *timeline,
            "",
            "## Tool Call Order",
            *([f"- {event['event_type']} ({event.get('call_id')})" for event in tool_calls] or ["- none"]),
            "",
            "## Assistant Message Flow",
            *([f"- {message[:160]}" for message in assistant_messages] or ["- none"]),
            "",
            "## Final Result",
            assistant_messages[-1] if assistant_messages else "none",
            "",
            "## Notes",
            notes or "none",
        ]
    )
