"""Normalization for Codex fixture traces."""

from __future__ import annotations

from pathlib import Path

from .io import read_jsonl
from .schema import build_event


def normalize_tui_fixture(path: Path) -> list[dict]:
    rows = read_jsonl(path)
    normalized: list[dict] = []
    current_turn_id: str | None = None
    buffered_user_input: list[str] = []

    for row in rows:
        ts = row["ts"]
        kind = row.get("kind")
        channel = row.get("dir", "unknown")

        if kind == "session_start":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="session_start",
                    payload={
                        "cwd": row.get("cwd"),
                        "model": row.get("model"),
                        "model_provider_id": row.get("model_provider_id"),
                    },
                    raw=row,
                )
            )
            continue

        if kind == "key_event":
            event = row.get("event", "")
            if "kind: Press" in event and "code: Char(" in event:
                start = event.find("code: Char('")
                if start != -1:
                    buffered_user_input.append(event[start + 12])
            elif "kind: Press" in event and "code: Enter" in event and buffered_user_input:
                text = "".join(buffered_user_input)
                normalized.append(
                    build_event(
                        ts=ts,
                        source="inferred",
                        channel=channel,
                        event_type="user_input",
                        turn_id=current_turn_id,
                        payload={"text": text},
                        raw={"inferred_from": "key_event_sequence", "events": text},
                    )
                )
                buffered_user_input = []
            continue

        if kind != "codex_event":
            continue

        payload = row.get("payload", {})
        msg = payload.get("msg", {})
        msg_type = msg.get("type")
        current_turn_id = payload.get("id", current_turn_id)

        if msg_type == "task_started":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="task_started",
                    turn_id=current_turn_id,
                    payload={},
                    raw=row,
                )
            )
        elif msg_type == "agent_message_delta":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="assistant_message_delta",
                    turn_id=current_turn_id,
                    payload={"delta": msg.get("delta", "")},
                    raw=row,
                )
            )
        elif msg_type == "agent_message":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="assistant_message",
                    turn_id=current_turn_id,
                    message_id=current_turn_id,
                    payload={"text": msg.get("message", "")},
                    raw=row,
                )
            )
        elif msg_type == "task_complete":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="task_complete",
                    turn_id=current_turn_id,
                    payload={"last_agent_message": msg.get("last_agent_message")},
                    raw=row,
                )
            )
        elif msg_type == "shutdown_complete":
            normalized.append(
                build_event(
                    ts=ts,
                    source="fixture",
                    channel=channel,
                    event_type="session_end",
                    turn_id=current_turn_id,
                    payload={},
                    raw=row,
                )
            )

    if rows and rows[-1].get("kind") == "session_end":
        row = rows[-1]
        normalized.append(
            build_event(
                ts=row["ts"],
                source="fixture",
                channel=row.get("dir", "meta"),
                event_type="session_end",
                turn_id=current_turn_id,
                payload={},
                raw=row,
            )
        )

    return normalized
