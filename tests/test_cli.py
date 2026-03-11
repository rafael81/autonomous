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
