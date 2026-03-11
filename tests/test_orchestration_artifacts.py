from pathlib import Path

from autonomos.orchestration import build_retry_appendix, write_request_user_input_artifact


def test_write_request_user_input_artifact_creates_json(tmp_path: Path):
    path = write_request_user_input_artifact(session_dir=tmp_path, prompt="Choose the better direction.")

    text = path.read_text(encoding="utf-8")
    assert path.name == "request-user-input.json"
    assert "Which direction should the run prioritize?" in text


def test_build_retry_appendix_includes_reason():
    text = build_retry_appendix("baseline mismatch remains high")

    assert "baseline mismatch remains high" in text
    assert "Retry guidance" in text
