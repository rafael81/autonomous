"""Shared schema definitions for normalized observation events."""

from __future__ import annotations

from typing import Final

NORMALIZED_EVENT_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "ts",
    "source",
    "channel",
    "event_type",
    "turn_id",
    "message_id",
    "call_id",
    "payload",
    "raw",
)

VALID_SOURCES: Final[set[str]] = {"live_capture", "fixture", "inferred"}


def build_event(
    *,
    ts: str,
    source: str,
    channel: str,
    event_type: str,
    payload: dict,
    raw: dict,
    turn_id: str | None = None,
    message_id: str | None = None,
    call_id: str | None = None,
) -> dict:
    if source not in VALID_SOURCES:
        raise ValueError(f"unsupported source: {source}")
    return {
        "ts": ts,
        "source": source,
        "channel": channel,
        "event_type": event_type,
        "turn_id": turn_id,
        "message_id": message_id,
        "call_id": call_id,
        "payload": payload,
        "raw": raw,
    }
