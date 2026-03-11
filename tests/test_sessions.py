from pathlib import Path

from autonomos.memory import MemoryTurn, append_session_memory, list_sessions


def test_list_sessions_reports_saved_histories(tmp_path: Path):
    append_session_memory(tmp_path, "alpha", [MemoryTurn(role="user", text="hello")])
    append_session_memory(tmp_path, "beta", [MemoryTurn(role="user", text="hi"), MemoryTurn(role="assistant", text="there")])

    sessions = list_sessions(tmp_path)

    assert ("alpha", 1) in sessions
    assert ("beta", 2) in sessions
