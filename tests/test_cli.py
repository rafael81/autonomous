import sys
from pathlib import Path

from autonomos import cli
from autonomos.io import write_jsonl


def test_chat_direct_profile_requires_openai_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello", "--profile", "autonomos_direct"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "OPENAI_API_KEY is required for direct OpenAI API runtime" in captured.err


def test_transcript_pretty_prints_tool_events(monkeypatch, capsys, tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"ts": "", "source": "fixture", "channel": "user", "event_type": "user_input", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "hello"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message_delta", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "do"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash", "args": {"command": "pwd"}}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash", "output": "ok"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
        ],
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "transcript", str(normalized)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "user> hello" in captured.out
    assert "tool> request bash" in captured.out
    assert "tool> result bash ok" in captured.out
    assert "assistant> done" in captured.out
    assert "final> done" in captured.out
    assert "assistant~ do" in captured.out


def test_sessions_latest_prints_most_recent(monkeypatch, capsys, tmp_path: Path):
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    write_jsonl(old, [{"role": "user", "text": "hello", "ts": "2026-03-11T00:00:00+00:00"}])
    write_jsonl(new, [{"role": "user", "text": "hi", "ts": "2026-03-11T01:00:00+00:00"}])
    monkeypatch.setattr(sys, "argv", ["autonomos", "sessions", "--memory-dir", str(tmp_path), "--latest"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "new"


def test_resolve_session_id_can_generate_new_id():
    session_id = cli._resolve_session_id("default", True)

    assert session_id.startswith("session-")
    assert session_id != "default"


def test_chat_new_session_uses_generated_id(monkeypatch, capsys, tmp_path: Path):
    captured_kwargs = {}

    class Summary:
        final_message = "hello"
        strategy_id = "simple_answer"
        baseline_example_id = "example"
        attempted_strategies = ["simple_answer"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 0
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "none"
        memory_path = None
        approval_request_path = None
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: captured_kwargs.update(kwargs) or Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello", "--new-session"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured_kwargs["session_id"].startswith("session-")
    assert "[session-id] session-" in captured.out
    assert "[closest-match] roma-simple-hello (score=0)" in captured.out


def test_chat_defaults_to_roma_runtime_profile(monkeypatch, capsys, tmp_path: Path):
    captured_kwargs = {}

    class Summary:
        final_message = "hello"
        strategy_id = "simple_answer"
        baseline_example_id = "example"
        attempted_strategies = ["simple_answer"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 0
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "none"
        memory_path = None
        approval_request_path = None
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: captured_kwargs.update(kwargs) or Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello"])

    exit_code = cli.main()

    assert exit_code == 0
    assert captured_kwargs["profile"] == "roma_ws"
