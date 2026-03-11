import json
from pathlib import Path

from autonomos.app import run_chat
from autonomos.io import write_jsonl
from autonomos.orchestration import (
    write_approval_artifact,
    write_approval_response,
    write_request_user_input_artifact,
    write_request_user_input_response,
)
from autonomos.roma_runtime import RomaChatResult


def test_run_chat_roma_includes_resume_artifacts_in_prompt(monkeypatch, tmp_path: Path):
    baselines_dir = tmp_path / "examples"
    baseline_dir = baselines_dir / "example-01-simple-short"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
        ],
    )
    request_path = write_request_user_input_artifact(session_dir=tmp_path, prompt="Choose a direction.")
    response_path = write_request_user_input_response(
        request_path=request_path,
        selected_option="Accuracy",
        notes="Prefer evidence.",
    )
    approval_request = write_approval_artifact(session_dir=tmp_path, prompt="Approve tool execution.")
    approval_response = write_approval_response(
        request_path=approval_request,
        decision="Approve",
        notes="Proceed.",
    )
    seen = {"prompt": None}

    def fake_run_roma_chat(**kwargs):
        seen["prompt"] = kwargs["prompt"]
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
        prompt="continue",
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines_dir,
        memory_dir=tmp_path / "memory",
        session_id="demo",
        request_user_input_response_path=response_path,
        approval_response_path=approval_response,
    )

    assert seen["prompt"] is not None
    assert "Accuracy" in seen["prompt"]
    assert "Prefer evidence." in seen["prompt"]
    assert "decision=Approve" in seen["prompt"]
