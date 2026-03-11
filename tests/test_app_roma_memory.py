from pathlib import Path

from autonomos.app import run_chat
from autonomos.io import write_jsonl
from autonomos.memory import MemoryTurn, append_session_memory
from autonomos.roma_runtime import RomaChatResult


def test_run_chat_roma_includes_memory_context_in_prompt_and_instructions(monkeypatch, tmp_path: Path):
    baselines_dir = tmp_path / "examples"
    baseline_dir = baselines_dir / "example-01-simple-short"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
        ],
    )
    append_session_memory(
        tmp_path / "memory",
        "demo",
        [
            MemoryTurn(role="user", text="remember this"),
            MemoryTurn(role="assistant", text="I will remember"),
        ],
    )
    seen: dict[str, str] = {}

    def fake_run_roma_chat(**kwargs):
        seen["prompt"] = kwargs["prompt"]
        seen["instructions"] = kwargs["instructions"]
        session_dir = tmp_path / "capture"
        session_dir.mkdir()
        normalized = session_dir / "normalized.jsonl"
        write_jsonl(
            normalized,
            [
                {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
            ],
        )
        return RomaChatResult(
            final_message="done",
            session_dir=session_dir,
            normalized_path=normalized,
            raw_jsonl_path=session_dir / "raw.jsonl",
            stdout_path=session_dir / "stdout.txt",
            stderr_path=session_dir / "stderr.txt",
            meta_path=session_dir / "meta.json",
        )

    monkeypatch.setattr("autonomos.app.run_roma_chat", fake_run_roma_chat)

    run_chat(
        prompt="what do you remember?",
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines_dir,
        memory_dir=tmp_path / "memory",
        session_id="demo",
    )

    assert "Recent conversation context:" in seen["prompt"]
    assert "- user: remember this" in seen["prompt"]
    assert "- assistant: I will remember" in seen["prompt"]
    assert "Recent conversation context:" in seen["instructions"]
