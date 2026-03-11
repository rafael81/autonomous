from pathlib import Path

from autonomos.exec_normalizer import normalize_exec_events
from autonomos.io import read_jsonl, write_jsonl


def test_normalize_exec_events_maps_core_flow():
    rows = [
        {"timestamp": "2026-03-11T00:00:00Z", "type": "thread.started", "thread_id": "thread-1"},
        {"timestamp": "2026-03-11T00:00:01Z", "type": "turn.started", "turn_id": "turn-1"},
        {
            "timestamp": "2026-03-11T00:00:02Z",
            "type": "item.started",
            "item": {
                "id": "cmd-1",
                "details": {
                    "type": "command_execution",
                    "command": "pwd",
                    "aggregated_output": "",
                    "status": "in_progress",
                    "exit_code": None,
                },
            },
        },
        {
            "timestamp": "2026-03-11T00:00:03Z",
            "type": "item.completed",
            "item": {
                "id": "cmd-1",
                "details": {
                    "type": "command_execution",
                    "command": "pwd",
                    "aggregated_output": "/tmp",
                    "status": "completed",
                    "exit_code": 0,
                },
            },
        },
        {
            "timestamp": "2026-03-11T00:00:04Z",
            "type": "item.completed",
            "item": {
                "id": "msg-1",
                "details": {
                    "type": "agent_message",
                    "text": "done",
                },
            },
        },
        {"timestamp": "2026-03-11T00:00:05Z", "type": "turn.completed", "usage": {"output_tokens": 1}},
    ]

    normalized = normalize_exec_events(rows)
    event_types = [event["event_type"] for event in normalized]

    assert event_types == [
        "session_start",
        "task_started",
        "tool_call_request",
        "tool_call_result",
        "assistant_message",
        "task_complete",
        "session_end",
    ]


def test_normalize_exec_cli_round_trip(tmp_path: Path):
    rows = [{"timestamp": "2026-03-11T00:00:00Z", "type": "thread.started", "thread_id": "thread-1"}]
    raw_path = tmp_path / "raw.jsonl"
    out_path = tmp_path / "normalized.jsonl"
    write_jsonl(raw_path, rows)

    normalized = normalize_exec_events(read_jsonl(raw_path))
    write_jsonl(out_path, normalized)

    loaded = read_jsonl(out_path)
    assert loaded[0]["event_type"] == "session_start"
    assert loaded[-1]["event_type"] == "session_end"


def test_normalize_exec_events_handles_direct_item_shape():
    rows = [
        {"timestamp": "2026-03-11T00:00:00Z", "type": "thread.started", "thread_id": "thread-1"},
        {"timestamp": "2026-03-11T00:00:01Z", "type": "turn.started", "turn_id": "turn-1"},
        {
            "timestamp": "2026-03-11T00:00:02Z",
            "type": "item.completed",
            "item": {
                "id": "msg-1",
                "type": "agent_message",
                "text": "hello",
            },
        },
        {
            "timestamp": "2026-03-11T00:00:03Z",
            "type": "item.completed",
            "item": {
                "id": "cmd-1",
                "type": "command_execution",
                "command": "/bin/zsh -lc 'ls -la'",
                "aggregated_output": "ok",
                "status": "completed",
                "exit_code": 0,
            },
        },
    ]

    normalized = normalize_exec_events(rows)

    assert [event["event_type"] for event in normalized] == [
        "session_start",
        "task_started",
        "assistant_message",
        "tool_call_result",
        "session_end",
    ]
    assert normalized[2]["payload"]["text"] == "hello"
    assert normalized[3]["payload"]["tool_name"] == "shell"
    assert normalized[3]["payload"]["command"] == "/bin/zsh -lc 'ls -la'"
