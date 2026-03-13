"""Simple local session memory for multi-turn chat."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path

from .io import read_jsonl, write_jsonl


@dataclass(frozen=True)
class MemoryTurn:
    role: str
    text: str


SUMMARY_ROLE = "summary"
SUMMARY_TRIGGER_TURNS = 10
SUMMARY_KEEP_RECENT = 6


def load_session_memory(memory_root: Path, session_id: str) -> list[MemoryTurn]:
    path = memory_root / f"{session_id}.jsonl"
    if not path.exists():
        return []
    rows = read_jsonl(path)
    return [MemoryTurn(role=row["role"], text=row["text"]) for row in rows]


def append_session_memory(memory_root: Path, session_id: str, turns: list[MemoryTurn]) -> Path:
    path = memory_root / f"{session_id}.jsonl"
    existing = []
    if path.exists():
        existing = read_jsonl(path)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    rows = existing + [{"role": turn.role, "text": turn.text, "ts": now} for turn in turns]
    rows = compact_session_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(path, rows)
    return path


def render_memory_context(turns: list[MemoryTurn], limit: int = 6) -> str:
    if not turns:
        return ""
    summary_turns = [turn for turn in turns if turn.role == SUMMARY_ROLE]
    conversational = [turn for turn in turns if turn.role != SUMMARY_ROLE]
    selected = conversational[-limit:]
    lines = ["Recent conversation context:"]
    if summary_turns:
        lines.append(summary_turns[-1].text)
    for turn in selected:
        lines.append(f"- {turn.role}: {turn.text}")
    return "\n".join(lines) + "\n\n"


def compact_session_rows(rows: list[dict]) -> list[dict]:
    conversational = [row for row in rows if row.get("role") in {"user", "assistant"}]
    if len(conversational) <= SUMMARY_TRIGGER_TURNS:
        return rows

    kept_recent = conversational[-SUMMARY_KEEP_RECENT:]
    recent_ids = {(row.get("ts"), row.get("role"), row.get("text")) for row in kept_recent}
    older = [
        row for row in conversational
        if (row.get("ts"), row.get("role"), row.get("text")) not in recent_ids
    ]
    if not older:
        return rows

    existing_summary = [row for row in rows if row.get("role") == SUMMARY_ROLE]
    summary_text = _summarize_rows((existing_summary[-1:] if existing_summary else []) + older)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    compacted: list[dict] = [row for row in rows if row.get("role") not in {"user", "assistant", SUMMARY_ROLE}]
    compacted.append({"role": SUMMARY_ROLE, "text": summary_text, "ts": now})
    compacted.extend(kept_recent)
    return compacted


def _summarize_rows(rows: list[dict]) -> str:
    user_points: list[str] = []
    assistant_points: list[str] = []
    decision_points: list[str] = []
    pending_points: list[str] = []
    for row in rows:
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        snippet = " ".join(text.split())[:160]
        if row.get("role") == "user":
            user_points.append(snippet)
        else:
            assistant_points.append(snippet)
        lowered = snippet.lower()
        if any(token in lowered for token in ("decided", "chosen", "selected", "approved", "direction", "plan")):
            decision_points.append(snippet)
        if any(token in lowered for token in ("next", "follow-up", "need", "pending", "continue", "wait")):
            pending_points.append(snippet)

    lines = ["Session summary:"]
    if user_points:
        lines.append("User focus:")
        lines.extend(f"- {item}" for item in user_points[-4:])
    if assistant_points:
        lines.append("Assistant progress:")
        lines.extend(f"- {item}" for item in assistant_points[-4:])
    if decision_points:
        lines.append("Decisions so far:")
        lines.extend(f"- {item}" for item in decision_points[-3:])
    if pending_points:
        lines.append("Open threads:")
        lines.extend(f"- {item}" for item in pending_points[-3:])
    return "\n".join(lines)


def list_sessions(memory_root: Path) -> list[tuple[str, int, str | None]]:
    if not memory_root.exists():
        return []
    sessions: list[tuple[str, int, str | None]] = []
    for path in sorted(memory_root.glob("*.jsonl")):
        rows = read_jsonl(path)
        count = len(rows)
        last_ts = rows[-1].get("ts") if rows else None
        sessions.append((path.stem, count, last_ts))
    return sorted(sessions, key=lambda item: (item[2] is None, item[2] or "", item[0]), reverse=True)
