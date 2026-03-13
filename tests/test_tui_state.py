from pathlib import Path

from autonomos.app import ChatRunSummary
from autonomos.io import write_jsonl
from autonomos.tui_state import TuiSessionState, build_transcript_lines


def test_build_transcript_lines_formats_status_tools_and_final(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"event_type": "user_input", "payload": {"text": "hello"}},
            {"event_type": "status_update", "payload": {"text": "Thinking..."}},
            {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir", "args": {"path": "."}}},
            {"event_type": "tool_call_result", "payload": {"tool_name": "list_dir", "output": "README.md\nsrc"}},
            {"event_type": "assistant_message", "payload": {"text": "done"}},
        ],
    )

    lines = build_transcript_lines(normalized)

    assert "user> hello" in lines
    assert "status> Thinking..." in lines
    assert "tool> request list_dir {'path': '.'}" in lines
    assert "tool> result list_dir README.md" in lines
    assert "assistant> done" in lines
    assert "final> done" in lines


def test_tui_session_state_applies_summary(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"event_type": "user_input", "payload": {"text": "hello"}},
            {"event_type": "assistant_message", "payload": {"text": "done"}},
        ],
    )
    summary = ChatRunSummary(
        final_message="done",
        strategy_id="simple_answer",
        baseline_example_id="codex-simple-hello",
        attempted_strategies=["simple_answer"],
        orchestration_summary="approval=no, request_user_input=no, retry=no",
        session_dir=tmp_path,
        normalized_path=normalized,
        promoted_example_dir=None,
        baseline_matches=1,
        baseline_total=10,
        comparison_summary_path=None,
        request_user_input_path=None,
        adaptive_notes="Attempt scores: [0]",
        memory_path=None,
        approval_request_path=None,
        closest_match_example_id="codex-simple-hello",
        closest_match_score=0,
        intended_match_example_id="codex-simple-hello",
        intended_match_score=0,
        drift_summary=None,
        drift_primary_causes=[],
        validation_hints=["Run tests"],
        runtime_diagnostics=["tool results captured"],
    )
    state = TuiSessionState(session_id="demo", memory_dir=tmp_path)

    state.apply_summary(summary)

    assert "assistant> done" in state.transcript_lines
    assert any(line.startswith("parity: exact match") for line in state.parity_lines)
    assert any("validation: Run tests" in line for line in state.diagnostics_lines)


def test_tui_session_state_deduplicates_existing_tail(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"event_type": "user_input", "payload": {"text": "hello"}},
            {"event_type": "status_update", "payload": {"text": "Roma is thinking..."}},
            {"event_type": "assistant_message", "payload": {"text": "done"}},
        ],
    )
    summary = ChatRunSummary(
        final_message="done",
        strategy_id="simple_answer",
        baseline_example_id="codex-simple-hello",
        attempted_strategies=["simple_answer"],
        orchestration_summary="approval=no, request_user_input=no, retry=no",
        session_dir=tmp_path,
        normalized_path=normalized,
        promoted_example_dir=None,
        baseline_matches=1,
        baseline_total=10,
        comparison_summary_path=None,
        request_user_input_path=None,
        adaptive_notes="Attempt scores: [0]",
        memory_path=None,
        approval_request_path=None,
        closest_match_example_id="codex-simple-hello",
        closest_match_score=0,
        intended_match_example_id="codex-simple-hello",
        intended_match_score=0,
        drift_summary=None,
        drift_primary_causes=[],
        validation_hints=[],
        runtime_diagnostics=[],
    )
    state = TuiSessionState(session_id="demo", memory_dir=tmp_path)
    state.add_user_prompt("hello")
    state.add_local_status("Roma is thinking...")

    state.apply_summary(summary)

    assert state.transcript_lines.count("user> hello") == 1
