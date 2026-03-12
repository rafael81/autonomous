import json
from pathlib import Path

from autonomos.regression import (
    build_regression_report,
    detect_tool_family,
    load_eval_suite,
    run_regression_suite,
)
from autonomos.io import write_jsonl


def test_load_eval_suite_reads_cases(tmp_path: Path):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            [
                {
                    "example_id": "hello",
                    "prompt": "say hello briefly",
                    "invocation_mode": "chat",
                    "memory_seed": None,
                    "expected_strategy": "simple_answer",
                    "expected_tool_family": "none",
                    "max_score": 0,
                    "expected_artifact": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_eval_suite(suite_path)

    assert len(cases) == 1
    assert cases[0].example_id == "hello"


def test_detect_tool_family_from_repo_tools(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}},
            {"event_type": "tool_call_request", "payload": {"tool_name": "read_file"}},
        ],
    )

    assert detect_tool_family(normalized) == "repo_inspection"


def test_run_regression_suite_uses_expected_checks(monkeypatch, tmp_path: Path):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            [
                {
                    "example_id": "hello",
                    "prompt": "say hello briefly",
                    "invocation_mode": "chat",
                    "memory_seed": None,
                    "expected_strategy": "simple_answer",
                    "expected_tool_family": "none",
                    "max_score": 0,
                    "expected_artifact": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    class Summary:
        strategy_id = "simple_answer"
        closest_match_example_id = "hello"
        closest_match_score = 0
        final_message = "hello"
        normalized_path = tmp_path / "captures" / "normalized.jsonl"
        session_dir = tmp_path / "capture"

    Summary.normalized_path.parent.mkdir(parents=True)
    write_jsonl(Summary.normalized_path, [])
    golden_dir = tmp_path / "goldens" / "hello"
    golden_dir.mkdir(parents=True)
    write_jsonl(golden_dir / "normalized.jsonl", [])

    monkeypatch.setattr("autonomos.regression.run_chat", lambda **kwargs: Summary())

    results = run_regression_suite(
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        goldens_dir=tmp_path / "goldens",
        suite_path=suite_path,
    )

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].expected_score == 0
    assert results[0].artifact_ok is True
    assert results[0].drift_summary == "No structured drift detected."


def test_run_regression_suite_uses_review_resolution_for_review_cases(monkeypatch, tmp_path: Path):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            [
                {
                    "example_id": "review",
                    "prompt": "Review only the current CLI changes.",
                    "invocation_mode": "review",
                    "memory_seed": None,
                    "expected_strategy": "tool_oriented",
                    "expected_tool_family": "review",
                    "max_score": 5,
                    "expected_artifact": None,
                }
            ]
        ),
        encoding="utf-8",
    )
    seen = {}

    class Summary:
        strategy_id = "tool_oriented"
        closest_match_example_id = "review"
        closest_match_score = 0
        final_message = "finding"
        normalized_path = tmp_path / "captures" / "normalized.jsonl"
        session_dir = tmp_path / "capture"

    Summary.normalized_path.parent.mkdir(parents=True)
    write_jsonl(
        Summary.normalized_path,
        [{"event_type": "tool_call_request", "payload": {"tool_name": "bash"}}],
    )
    golden_dir = tmp_path / "goldens" / "review"
    golden_dir.mkdir(parents=True)
    write_jsonl(
        golden_dir / "normalized.jsonl",
        [{"event_type": "tool_call_request", "payload": {"tool_name": "bash"}}],
    )

    monkeypatch.setattr("autonomos.regression.resolve_review_request", lambda **kwargs: type("Req", (), {"prompt": "resolved review prompt"})())
    monkeypatch.setattr("autonomos.regression.run_chat", lambda **kwargs: seen.update(kwargs) or Summary())

    results = run_regression_suite(
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        goldens_dir=tmp_path / "goldens",
        suite_path=suite_path,
    )

    assert results[0].passed is True
    assert seen["prompt"] == "resolved review prompt"


def test_run_regression_suite_seeds_memory_and_checks_artifact(monkeypatch, tmp_path: Path):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            [
                {
                    "example_id": "rui",
                    "prompt": "Choose the better direction for this plan",
                    "invocation_mode": "chat",
                    "memory_seed": [{"role": "user", "text": "Remember my earlier note."}],
                    "expected_strategy": "planning",
                    "expected_tool_family": "none",
                    "max_score": 0,
                    "expected_artifact": "request_user_input",
                }
            ]
        ),
        encoding="utf-8",
    )

    class Summary:
        strategy_id = "planning"
        closest_match_example_id = "rui"
        closest_match_score = 0
        final_message = "done"
        normalized_path = tmp_path / "captures" / "normalized.jsonl"
        session_dir = tmp_path / "capture"
        request_user_input_path = tmp_path / "capture" / "request-user-input.json"
        approval_request_path = None

    Summary.normalized_path.parent.mkdir(parents=True)
    Summary.request_user_input_path.parent.mkdir(parents=True, exist_ok=True)
    Summary.request_user_input_path.write_text("{}", encoding="utf-8")
    write_jsonl(Summary.normalized_path, [])
    golden_dir = tmp_path / "goldens" / "rui"
    golden_dir.mkdir(parents=True)
    write_jsonl(golden_dir / "normalized.jsonl", [])

    monkeypatch.setattr("autonomos.regression.run_chat", lambda **kwargs: Summary())

    results = run_regression_suite(
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        goldens_dir=tmp_path / "goldens",
        suite_path=suite_path,
    )

    assert results[0].artifact_ok is True
    assert results[0].passed is True


def test_build_regression_report_lists_failures():
    rows = build_regression_report(
        [
            type(
                "Obj",
                (),
                {
                    "passed": False,
                    "example_id": "hello",
                    "prompt": "say hello briefly",
                    "expected_strategy": "simple_answer",
                    "actual_strategy": "planning",
                    "expected_tool_family": "none",
                    "actual_tool_family": "none",
                    "expected_artifact": "request_user_input",
                    "artifact_present": False,
                    "expected_score": 4,
                    "closest_match_example_id": "roma-simple-hello",
                    "closest_match_score": 3,
                    "drift_summary": "tool_routing: expected tool order=['list_dir'] actual=[]",
                    "primary_causes": ["tool_routing"],
                    "artifact_ok": False,
                    "session_dir": "captures/demo",
                    "normalized_path": "captures/demo/normalized.jsonl",
                },
            )()
        ]
    )

    assert "FAIL hello" in rows
    assert "strategy: expected=simple_answer actual=planning" in rows
    assert "artifact: expected=request_user_input present=no" in rows
    assert "expected_golden_score: 4" in rows
    assert "drift: tool_routing: expected tool order=['list_dir'] actual=[]" in rows
