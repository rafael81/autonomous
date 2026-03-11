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


def test_normalize_roma_events_preserves_builtin_tool_names():
    rows = normalize_roma_events(
        prompt="inspect repo",
        raw_events=[
            {"type": "tool_call", "name": "list_dir", "callId": "call-1", "args": {"path": "."}},
            {"type": "tool_result", "name": "list_dir", "callId": "call-1", "output": "file\tREADME.md"},
            {"type": "tool_call", "name": "read_file", "callId": "call-2", "args": {"path": "README.md"}},
            {"type": "tool_result", "name": "read_file", "callId": "call-2", "output": "1: # autonomos"},
            {"type": "tool_call", "name": "grep_text", "callId": "call-3", "args": {"pattern": "autonomos"}},
            {"type": "tool_result", "name": "grep_text", "callId": "call-3", "output": "README.md:1: # autonomos"},
            {"type": "session_end", "ok": True},
        ],
    )

    tool_names = [row["payload"].get("tool_name") for row in rows if "tool_call" in row["event_type"]]
    assert tool_names == ["list_dir", "list_dir", "read_file", "read_file", "grep_text", "grep_text"]
