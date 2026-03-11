import json
from pathlib import Path

from autonomos.cli import _handle_inline_approval, _handle_inline_request_user_input


def test_handle_inline_request_user_input(monkeypatch, tmp_path: Path):
    request = tmp_path / "request-user-input.json"
    request.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "question": "Which direction?",
                        "options": [
                            {"label": "Speed", "description": "fast"},
                            {"label": "Accuracy", "description": "careful"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    answers = iter(["2", "prefer evidence"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    response = _handle_inline_request_user_input(request)

    assert response is not None
    payload = json.loads(response.read_text(encoding="utf-8"))
    assert payload["answers"][0]["selected_option"] == "Accuracy"


def test_handle_inline_approval(monkeypatch, tmp_path: Path):
    request = tmp_path / "approval-request.json"
    request.write_text(
        json.dumps(
            {
                "question": "Approve tool execution?",
                "options": [
                    {"label": "Approve", "description": "go"},
                    {"label": "Decline", "description": "stop"},
                ],
            }
        ),
        encoding="utf-8",
    )
    answers = iter(["2", "not now"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    response = _handle_inline_approval(request)

    assert response is not None
    payload = json.loads(response.read_text(encoding="utf-8"))
    assert payload["decision"] == "Decline"
