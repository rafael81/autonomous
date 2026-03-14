from autonomos.memory import MemoryTurn, append_session_memory, load_session_memory, render_memory_context


def test_append_session_memory_compacts_long_sessions(tmp_path):
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
    loaded = load_session_memory(memory_dir, session_id)

    assert any(turn.role == "summary" for turn in loaded)
    assert loaded[-1].role == "assistant"
    assert len([turn for turn in loaded if turn.role in {"user", "assistant"}]) <= 6


def test_render_memory_context_includes_summary_and_recent_turns(tmp_path):
    memory_dir = tmp_path / "memory"
    session_id = "demo"
    turns = []
    for idx in range(12):
        turns.extend(
            [
                MemoryTurn(role="user", text=f"user turn {idx} with plan choice"),
                MemoryTurn(role="assistant", text=f"assistant turn {idx} next step pending"),
            ]
        )

    append_session_memory(memory_dir, session_id, turns)
    loaded = load_session_memory(memory_dir, session_id)
    rendered = render_memory_context(loaded)

    assert "Session summary:" in rendered
    assert "Decisions so far:" in rendered
    assert "Open threads:" in rendered


def test_render_memory_context_skips_failed_output_turns():
    rendered = render_memory_context(
        [
            MemoryTurn(role="summary", text="Session summary:\n- No output generated. Check the stream for errors."),
            MemoryTurn(role="assistant", text="No output generated. Check the stream for errors."),
            MemoryTurn(role="user", text="hello"),
            MemoryTurn(role="assistant", text="Hi there"),
        ]
    )

    assert "No output generated" not in rendered
    assert "- user: hello" in rendered
    assert "- assistant: Hi there" in rendered
