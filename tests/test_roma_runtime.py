from pathlib import Path

from autonomos.memory import MemoryTurn
from autonomos.roma_runtime import normalize_roma_events


def test_normalize_roma_events_maps_bridge_events():
    rows = normalize_roma_events(
        prompt="hello",
        raw_events=[
            {"type": "assistant_message_delta", "text": "hel"},
            {"type": "tool_call", "name": "bash", "callId": "call-1", "args": {"command": "pwd"}},
            {"type": "tool_result", "name": "bash", "callId": "call-1", "output": "ok"},
            {"type": "assistant_message", "text": "hello"},
            {"type": "session_end", "ok": True},
        ],
    )

    assert [row["event_type"] for row in rows] == [
        "session_start",
        "user_input",
        "task_started",
        "assistant_message_delta",
        "tool_call_request",
        "tool_call_result",
        "assistant_message",
        "task_complete",
        "session_end",
    ]
    assert rows[4]["payload"]["tool_name"] == "bash"
    assert rows[6]["payload"]["text"] == "hello"
