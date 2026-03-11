from pathlib import Path

from autonomos.app import run_chat
from autonomos.io import write_jsonl
from autonomos.roma_runtime import RomaChatResult


def test_run_chat_roma_short_circuits_after_simple_answer_success(monkeypatch, tmp_path: Path):
    baselines_dir = tmp_path / "examples"
    baseline_dir = baselines_dir / "example-01-simple-short"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {
                "ts": "",
                "source": "fixture",
                "channel": "assistant",
                "event_type": "assistant_message",
                "turn_id": None,
                "message_id": None,
                "call_id": None,
                "payload": {"text": "hello"},
                "raw": {},
            },
        ],
    )
    call_count = {"value": 0}

    def fake_run_roma_chat(**kwargs):
        call_count["value"] += 1
        session_dir = tmp_path / f"capture-{call_count['value']}"
        session_dir.mkdir()
        normalized = session_dir / "normalized.jsonl"
        write_jsonl(
            normalized,
            [
                {
                    "ts": "",
                    "source": "fixture",
                    "channel": "assistant",
                    "event_type": "assistant_message",
                    "turn_id": None,
                    "message_id": None,
                    "call_id": None,
                    "payload": {"text": "안녕하세요"},
                    "raw": {},
                },
            ],
        )
        return RomaChatResult(
            final_message="안녕하세요",
            session_dir=session_dir,
            normalized_path=normalized,
            raw_jsonl_path=session_dir / "raw.jsonl",
            stdout_path=session_dir / "stdout.txt",
            stderr_path=session_dir / "stderr.txt",
            meta_path=session_dir / "meta.json",
        )

    monkeypatch.setattr("autonomos.app.run_roma_chat", fake_run_roma_chat)

    summary = run_chat(
        prompt="안녕",
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines_dir,
        memory_dir=tmp_path / "memory",
        session_id="demo",
    )

    assert call_count["value"] == 1
    assert summary.attempted_strategies == ["simple_answer"]
    assert summary.final_message == "안녕하세요"
