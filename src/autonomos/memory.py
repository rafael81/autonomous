"""Simple local session memory for multi-turn chat."""

from __future__ import annotations

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
    rows = existing + [{"role": turn.role, "text": turn.text} for turn in turns]
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
