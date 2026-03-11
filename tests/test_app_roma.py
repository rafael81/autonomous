from pathlib import Path

from autonomos.app import run_chat
from autonomos.io import write_jsonl
from autonomos.roma_runtime import RomaChatResult


def test_run_chat_uses_roma_runtime_for_roma_profile(monkeypatch, tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "hello from roma"}, "raw": {}},
        ],
    )
    example_dir = tmp_path / "examples" / "example-01-simple-short"
    example_dir.mkdir(parents=True)
    write_jsonl(
        example_dir / "normalized.jsonl",
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "baseline"}, "raw": {}},
        ],
    )

    def fake_run_roma_chat(**kwargs):
        session_dir = tmp_path / "capture"
        session_dir.mkdir()
        return RomaChatResult(
            final_message="hello from roma",
            session_dir=session_dir,
            normalized_path=normalized,
            raw_jsonl_path=session_dir / "raw.jsonl",
            stdout_path=session_dir / "stdout.txt",
            stderr_path=session_dir / "stderr.txt",
            meta_path=session_dir / "meta.json",
        )

    monkeypatch.setattr("autonomos.app.run_roma_chat", fake_run_roma_chat)

    summary = run_chat(
        prompt="hello",
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        session_id="demo",
    )

    assert summary.final_message == "hello from roma"
    assert summary.baseline_total == 1
    assert summary.adaptive_notes == "Attempt scores: [0]"
