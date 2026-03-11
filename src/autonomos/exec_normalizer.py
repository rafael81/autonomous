"""Normalize `codex exec --json` output into the shared event schema."""

from __future__ import annotations

from .schema import build_event


def normalize_exec_events(rows: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    current_turn_id: str | None = None

    for row in rows:
        event_type = row.get("type")
        ts = row.get("timestamp", "")

        if event_type == "thread.started":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="session_start",
                    turn_id=row.get("thread_id"),
                    payload={"thread_id": row.get("thread_id")},
                    raw=row,
                )
            )
            continue

        if event_type == "turn.started":
            current_turn_id = row.get("turn_id", current_turn_id)
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="task_started",
                    turn_id=current_turn_id,
                    payload={},
                    raw=row,
                )
            )
            continue

        if event_type == "turn.completed":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="task_complete",
                    turn_id=current_turn_id,
                    payload={"usage": row.get("usage", {})},
                    raw=row,
                )
            )
            continue

        if event_type == "turn.failed":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="task_complete",
                    turn_id=current_turn_id,
                    payload={"error": row.get("error", {})},
                    raw=row,
                )
            )
            continue

        if event_type not in {"item.started", "item.updated", "item.completed"}:
            if event_type == "error":
                normalized.append(
                    build_event(
                        ts=ts,
                        source="live_capture",
                        channel="exec",
                        event_type="session_end",
                        turn_id=current_turn_id,
                        payload={"error": row.get("message")},
                        raw=row,
                    )
                )
            continue

        item = row.get("item", {})
        details = item.get("details", {})
        item_type = details.get("type")
        item_id = item.get("id")

        if item_type == "agent_message":
            text = details.get("text", "")
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="assistant_message",
                    turn_id=current_turn_id,
                    message_id=item_id,
                    payload={"text": text},
                    raw=row,
                )
            )
        elif item_type == "command_execution":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="tool_call_request" if event_type == "item.started" else "tool_call_result",
                    turn_id=current_turn_id,
                    call_id=item_id,
                    payload={
                        "tool_name": "shell",
                        "command": details.get("command"),
                        "output": details.get("aggregated_output"),
                        "status": details.get("status"),
                        "exit_code": details.get("exit_code"),
                    },
                    raw=row,
                )
            )
        elif item_type == "mcp_tool_call":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="tool_call_request" if event_type == "item.started" else "tool_call_result",
                    turn_id=current_turn_id,
                    call_id=item_id,
                    payload={
                        "tool_name": details.get("name"),
                        "arguments": details.get("arguments"),
                        "status": details.get("status"),
                        "result": details.get("result"),
                        "error": details.get("error"),
                    },
                    raw=row,
                )
            )
        elif item_type == "file_change":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="tool_call_result",
                    turn_id=current_turn_id,
                    call_id=item_id,
                    payload={
                        "tool_name": "apply_patch",
                        "changes": details.get("changes", []),
                        "status": details.get("status"),
                    },
                    raw=row,
                )
            )
        elif item_type == "todo_list":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="assistant_message",
                    turn_id=current_turn_id,
                    message_id=item_id,
                    payload={"text": f"TODO_LIST {details.get('items', [])}"},
                    raw=row,
                )
            )
        elif item_type == "web_search":
            normalized.append(
                build_event(
                    ts=ts,
                    source="live_capture",
                    channel="exec",
                    event_type="tool_call_request" if event_type == "item.started" else "tool_call_result",
                    turn_id=current_turn_id,
                    call_id=item_id,
                    payload={
                        "tool_name": "web_search",
                        "query": details.get("query"),
                        "status": details.get("status"),
                    },
                    raw=row,
                )
            )

    if normalized and normalized[-1]["event_type"] != "session_end":
        last = normalized[-1]
        normalized.append(
            build_event(
                ts=last["ts"],
                source="inferred",
                channel="exec",
                event_type="session_end",
                turn_id=last["turn_id"],
                payload={},
                raw={"inferred_from": "exec_stream_end"},
            )
        )

    return normalized
