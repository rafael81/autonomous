from pathlib import Path

from autonomos.cli import _read_session_summary
from autonomos.memory import MemoryTurn, append_session_memory


def test_read_session_summary_returns_compacted_summary(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    session_id = "demo"
    turns = []
    for idx in range(12):
        turns.extend(
            [
                MemoryTurn(role="user", text=f"user turn {idx}"),
                MemoryTurn(role="assistant", text=f"assistant turn {idx}"),
            ]
        )
    append_session_memory(memory_dir, session_id, turns)

    summary = _read_session_summary(memory_dir, session_id)

    assert summary == "Session summary:"
