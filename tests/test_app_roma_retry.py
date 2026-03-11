from pathlib import Path

from autonomos.app import run_chat
from autonomos.io import write_jsonl
from autonomos.roma_runtime import RomaChatResult


def test_run_chat_roma_can_try_multiple_strategies(monkeypatch, tmp_path: Path):
    baselines_dir = tmp_path / "examples"
    baseline_dir = baselines_dir / "example-03-single-tool"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {"ts": "", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
            {"ts": "", "source": "inferred", "channel": "x", "event_type": "session_end", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
        ],
    )
    call_count = {"value": 0}

    def fake_run_roma_chat(**kwargs):
        call_count["value"] += 1
        session_dir = tmp_path / f"capture-{call_count['value']}"
        session_dir.mkdir()
        normalized = session_dir / "normalized.jsonl"
        if call_count["value"] == 1:
            rows = [
                {"ts": "", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
                {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "plan"}, "raw": {}},
                {"ts": "", "source": "inferred", "channel": "x", "event_type": "session_end", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
            ]
        else:
            rows = [
                {"ts": "", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
                {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash"}, "raw": {}},
                {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash"}, "raw": {}},
                {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
                {"ts": "", "source": "inferred", "channel": "x", "event_type": "session_end", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
            ]
        write_jsonl(normalized, rows)
        return RomaChatResult(
            final_message="done" if call_count["value"] > 1 else "plan",
            session_dir=session_dir,
            normalized_path=normalized,
            raw_jsonl_path=session_dir / "raw.jsonl",
            stdout_path=session_dir / "stdout.txt",
            stderr_path=session_dir / "stderr.txt",
            meta_path=session_dir / "meta.json",
        )

    monkeypatch.setattr("autonomos.app.run_roma_chat", fake_run_roma_chat)

    summary = run_chat(
        prompt="Make a plan for checking this repository and verify the tests.",
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines_dir,
        memory_dir=tmp_path / "memory",
        session_id="demo",
    )

    assert call_count["value"] >= 2
    assert summary.attempted_strategies[:2] == ["planning", "tool_oriented"]
    assert summary.final_message == "done"
