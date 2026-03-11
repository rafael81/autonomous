from pathlib import Path

from autonomos.orchestration import (
    render_request_user_input_response,
    write_request_user_input_artifact,
    write_request_user_input_response,
)


def test_request_user_input_response_round_trip(tmp_path: Path):
    request = write_request_user_input_artifact(session_dir=tmp_path, prompt="Choose a direction.")
    response = write_request_user_input_response(
        request_path=request,
        selected_option="Accuracy",
        notes="Prefer evidence.",
    )

    rendered = render_request_user_input_response(response)

    assert response.exists()
    assert "Accuracy" in rendered
    assert "Prefer evidence." in rendered
