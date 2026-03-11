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
    path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(path, rows)
    return path


def render_memory_context(turns: list[MemoryTurn], limit: int = 6) -> str:
    if not turns:
        return ""
    selected = turns[-limit:]
    lines = ["Recent conversation context:"]
    for turn in selected:
        lines.append(f"- {turn.role}: {turn.text}")
    return "\n".join(lines) + "\n\n"


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
