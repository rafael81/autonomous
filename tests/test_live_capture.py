import json
from pathlib import Path

from autonomos.live_capture import LiveCaptureResult, save_capture_session


def test_save_capture_session_writes_text_outputs(tmp_path: Path):
    result = LiveCaptureResult(
        command=["codex", "exec", "--json", "hello"],
        returncode=0,
        stdout="plain text output\n",
        stderr="warnings\n",
    )

    saved = save_capture_session(result=result, prompt="hello", output_root=tmp_path)

    assert saved.prompt_path.read_text(encoding="utf-8").strip() == "hello"
    assert saved.raw_stdout_path.read_text(encoding="utf-8") == "plain text output\n"
    assert saved.raw_stderr_path.read_text(encoding="utf-8") == "warnings\n"
    assert saved.raw_jsonl_path is None
    assert saved.normalized_path is None


def test_save_capture_session_normalizes_jsonl_stdout(tmp_path: Path):
    stdout = "\n".join(
        [
            json.dumps({"timestamp": "2026-03-11T00:00:00Z", "type": "thread.started", "thread_id": "thread-1"}),
            json.dumps({"timestamp": "2026-03-11T00:00:01Z", "type": "turn.started", "turn_id": "turn-1"}),
        ]
    )
    result = LiveCaptureResult(
        command=["codex", "exec", "--json", "hello"],
        returncode=0,
        stdout=stdout + "\n",
        stderr="",
    )

    saved = save_capture_session(result=result, prompt="hello", output_root=tmp_path)

    assert saved.raw_jsonl_path is not None
    assert saved.normalized_path is not None
    normalized = saved.normalized_path.read_text(encoding="utf-8")
    assert '"event_type": "session_start"' in normalized
    assert '"event_type": "session_end"' in normalized
