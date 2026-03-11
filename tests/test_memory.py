from pathlib import Path

from autonomos.memory import MemoryTurn, append_session_memory, load_session_memory, render_memory_context


def test_memory_round_trip(tmp_path: Path):
    path = append_session_memory(tmp_path, "session-1", [MemoryTurn(role="user", text="hello")])
    turns = load_session_memory(tmp_path, "session-1")

    assert path.exists()
    assert turns == [MemoryTurn(role="user", text="hello")]


def test_render_memory_context_limits_recent_turns():
    turns = [MemoryTurn(role="user", text=f"u{i}") for i in range(8)]
    text = render_memory_context(turns, limit=3)

    assert "u7" in text
    assert "u0" not in text
