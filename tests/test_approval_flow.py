from pathlib import Path

from autonomos.orchestration import render_approval_response, write_approval_artifact, write_approval_response


def test_approval_response_round_trip(tmp_path: Path):
    request = write_approval_artifact(session_dir=tmp_path, prompt="Run a risky tool.")
    response = write_approval_response(request_path=request, decision="Approve", notes="Proceed.")

    rendered = render_approval_response(response)

    assert response.exists()
    assert "decision=Approve" in rendered
    assert "Proceed." in rendered
