import json
from pathlib import Path

from autonomos.cli import _handle_inline_approval, _handle_inline_request_user_input, _handle_repl_follow_up


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


def test_handle_repl_follow_up_runs_resume(monkeypatch, tmp_path: Path):
    approval_request = tmp_path / "approval-request.json"
    approval_request.write_text(
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
    calls = []

    class Summary:
        final_message = "initial"
        strategy_id = "tool_oriented"
        baseline_example_id = "example"
        orchestration_summary = "approval=yes, request_user_input=yes, retry=no"
        request_user_input_path = request
        approval_request_path = approval_request

    class FollowUpSummary:
        final_message = "continued"
        strategy_id = "simple_answer"
        baseline_example_id = "example"
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        request_user_input_path = None
        approval_request_path = None

    answers = iter(["1", "looks safe", "2", "prefer evidence"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(
        "autonomos.cli.run_chat",
        lambda **kwargs: calls.append(kwargs) or FollowUpSummary(),
    )

    result = _handle_repl_follow_up(
        summary=Summary(),
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        session_id="demo",
    )

    assert result.final_message == "continued"
    assert len(calls) == 1
    assert calls[0]["prompt"] == "continue"
    assert calls[0]["approval_response_path"] is not None
    assert calls[0]["request_user_input_response_path"] is not None
