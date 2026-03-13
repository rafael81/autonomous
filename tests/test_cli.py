import sys
from pathlib import Path

from autonomos import cli
from autonomos.io import write_jsonl


def test_chat_direct_profile_requires_openai_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello", "--profile", "autonomos_direct"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "OPENAI_API_KEY is required for direct OpenAI API runtime" in captured.err


def test_transcript_pretty_prints_tool_events(monkeypatch, capsys, tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"ts": "", "source": "fixture", "channel": "user", "event_type": "user_input", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "hello"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message_delta", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "do"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash", "args": {"command": "pwd"}}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash", "output": "ok"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "done"}, "raw": {}},
        ],
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "transcript", str(normalized)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "user> hello" in captured.out
    assert "tool> request bash" in captured.out
    assert "tool> result bash ok" in captured.out
    assert "assistant> done" in captured.out
    assert "final> done" in captured.out
    assert "assistant~ do" in captured.out


def test_sessions_latest_prints_most_recent(monkeypatch, capsys, tmp_path: Path):
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    write_jsonl(old, [{"role": "user", "text": "hello", "ts": "2026-03-11T00:00:00+00:00"}])
    write_jsonl(new, [{"role": "user", "text": "hi", "ts": "2026-03-11T01:00:00+00:00"}])
    monkeypatch.setattr(sys, "argv", ["autonomos", "sessions", "--memory-dir", str(tmp_path), "--latest"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "new"


def test_sessions_show_summary_prints_compacted_summary(monkeypatch, capsys, tmp_path: Path):
    write_jsonl(
        tmp_path / "demo.jsonl",
        [
            {"role": "summary", "text": "Session summary:\n- prior work", "ts": "2026-03-11T01:00:00+00:00"},
            {"role": "user", "text": "hi", "ts": "2026-03-11T01:01:00+00:00"},
        ],
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "sessions", "--memory-dir", str(tmp_path), "--show-summary"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Session summary:" in captured.out


def test_resolve_session_id_can_generate_new_id():
    session_id = cli._resolve_session_id("default", True)

    assert session_id.startswith("session-")
    assert session_id != "default"


def test_chat_new_session_uses_generated_id(monkeypatch, capsys, tmp_path: Path):
    captured_kwargs = {}

    class Summary:
        final_message = "hello"
        strategy_id = "simple_answer"
        baseline_example_id = "example"
        attempted_strategies = ["simple_answer"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 0
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "none"
        memory_path = None
        approval_request_path = None
        intended_match_example_id = "codex-simple-hello"
        intended_match_score = 0
        drift_summary = None
        drift_primary_causes = []
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: captured_kwargs.update(kwargs) or Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello", "--new-session"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured_kwargs["session_id"].startswith("session-")
    assert "[strategy] simple_answer -> codex-simple-hello" in captured.out
    assert "[session-id] session-" in captured.out
    assert "[parity] exact match for codex-simple-hello" in captured.out
    assert "[coverage] 0/0 aligned traces" in captured.out
    assert "[intended-golden] codex-simple-hello (score=0)" in captured.out
    assert "[drift] aligned" in captured.out
    assert "[closest-match] roma-simple-hello (score=0)" in captured.out


def test_chat_defaults_to_roma_runtime_profile(monkeypatch, capsys, tmp_path: Path):
    captured_kwargs = {}

    class Summary:
        final_message = "hello"
        strategy_id = "simple_answer"
        baseline_example_id = "example"
        attempted_strategies = ["simple_answer"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 0
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "none"
        memory_path = None
        approval_request_path = None
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: captured_kwargs.update(kwargs) or Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello"])

    exit_code = cli.main()

    assert exit_code == 0
    assert captured_kwargs["profile"] == "roma_ws"
    assert captured_kwargs["baselines_dir"] == Path("goldens")


def test_runtime_commands_default_to_goldens_baselines():
    parser = cli.build_parser()

    chat_args = parser.parse_args(["chat", "hello"])
    review_args = parser.parse_args(["review"])
    resume_args = parser.parse_args(["resume", "continue", "--response-file", "response.json"])
    repl_args = parser.parse_args(["repl"])

    assert chat_args.baselines_dir == "goldens"
    assert review_args.baselines_dir == "goldens"
    assert resume_args.baselines_dir == "goldens"
    assert repl_args.baselines_dir == "goldens"


def test_observe_commands_keep_examples_baselines():
    parser = cli.build_parser()

    observe_args = parser.parse_args(["observe", "inspect repo"])
    compare_args = parser.parse_args(["compare-baselines", "normalized.jsonl"])

    assert observe_args.baselines_dir == "examples"
    assert compare_args.baselines_dir == "examples"


def test_review_command_uses_resolved_review_prompt(monkeypatch, capsys, tmp_path: Path):
    captured_kwargs = {}

    class Summary:
        final_message = "finding"
        strategy_id = "tool_oriented"
        baseline_example_id = "example"
        attempted_strategies = ["tool_oriented"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 0
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "none"
        memory_path = None
        approval_request_path = None
        closest_match_example_id = "codex-project-analysis"
        closest_match_score = 1

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: captured_kwargs.update(kwargs) or Summary())
    monkeypatch.setattr(
        "autonomos.cli.resolve_review_request",
        lambda **kwargs: type("Req", (), {"prompt": "Review the current code changes.", "user_facing_hint": "current changes"})(),
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "review"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured_kwargs["prompt"] == "Review the current code changes."
    assert "[review-target] current changes" in captured.out


def test_chat_prints_drift_metadata_when_present(monkeypatch, capsys, tmp_path: Path):
    class Summary:
        final_message = "summary"
        strategy_id = "tool_oriented"
        baseline_example_id = "example-03-single-tool"
        attempted_strategies = ["tool_oriented"]
        orchestration_summary = "approval=no, request_user_input=no, retry=yes"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 10
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "Attempt scores: [3]"
        memory_path = None
        approval_request_path = None
        intended_match_example_id = "codex-readme-inspection"
        intended_match_score = 3
        drift_summary = "tool_routing: same inspection family, but the runtime used a shorter built-in tool path (1 steps) than the Codex golden (1 steps)"
        drift_primary_causes = ["tool_routing", "final_answer_formatting"]
        closest_match_example_id = "codex-readme-inspection"
        closest_match_score = 3

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "inspect the repo"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[strategy] tool_oriented -> codex-readme-inspection" in captured.out
    assert "[parity] drift from codex-readme-inspection (score=3)" in captured.out
    assert "[coverage] 0/10 aligned traces" in captured.out
    assert "[intended-golden] codex-readme-inspection (score=3)" in captured.out
    assert "[drift] tool_routing: same inspection family, but the runtime used a shorter built-in tool path" in captured.out
    assert "[drift-causes] tool_routing, final_answer_formatting" in captured.out


def test_chat_strategy_label_falls_back_to_closest_match(monkeypatch, capsys, tmp_path: Path):
    class Summary:
        final_message = "summary"
        strategy_id = "tool_oriented"
        baseline_example_id = "example-03-single-tool"
        attempted_strategies = ["tool_oriented"]
        orchestration_summary = "approval=no, request_user_input=no, retry=no"
        session_dir = tmp_path / "capture"
        normalized_path = None
        promoted_example_dir = None
        baseline_matches = 0
        baseline_total = 10
        comparison_summary_path = None
        request_user_input_path = None
        adaptive_notes = "Attempt scores: [3]"
        memory_path = None
        approval_request_path = None
        intended_match_example_id = None
        intended_match_score = None
        drift_summary = None
        drift_primary_causes = []
        closest_match_example_id = "codex-project-structure-analysis"
        closest_match_score = 2

    monkeypatch.setattr("autonomos.cli.run_chat", lambda **kwargs: Summary())
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "inspect the repo"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[strategy] tool_oriented -> codex-project-structure-analysis" in captured.out
    assert "[parity] closest golden is codex-project-structure-analysis (score=2)" in captured.out
    assert "[coverage] 0/10 aligned traces" in captured.out


def test_import_capture_golden_uses_prompt_file(monkeypatch, capsys, tmp_path: Path):
    capture_dir = tmp_path / "capture"
    capture_dir.mkdir()
    (capture_dir / "prompt.txt").write_text("say hello briefly\n", encoding="utf-8")
    write_jsonl(capture_dir / "normalized.jsonl", [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autonomos",
            "import-capture-golden",
            str(capture_dir),
            "hello-golden",
            "--output-dir",
            str(tmp_path / "goldens"),
        ],
    )

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "hello-golden" in captured.out
    assert (tmp_path / "goldens" / "hello-golden" / "prompt.txt").exists()


def test_show_eval_suite_prints_cases(monkeypatch, capsys, tmp_path: Path):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        '[{"example_id":"hello","prompt":"say hello briefly","invocation_mode":"chat","memory_seed":null,"expected_strategy":"simple_answer","expected_tool_family":"none","max_score":0,"expected_artifact":null}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "show-eval-suite", "--suite-path", str(suite_path)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "hello\tsimple_answer\tnone\tartifact=none\tmax_score=0\tsay hello briefly" in captured.out


def test_show_core_families_prints_configured_rows(monkeypatch, capsys, tmp_path: Path):
    families_path = tmp_path / "families.json"
    families_path.write_text(
        '[{"family_id":"hello","prompt":"say hello briefly","invocation_mode":"chat","expected_strategy":"simple_answer","expected_tool_family":"none","max_score":0,"expected_artifact":null,"notes":"demo"}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "show-core-families", "--families-path", str(families_path)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "hello\tchat\tsimple_answer\tnone\tmax_score=0\tsay hello briefly" in captured.out


def test_analyze_drift_prints_categories(monkeypatch, capsys, tmp_path: Path):
    expected = tmp_path / "expected.jsonl"
    actual = tmp_path / "actual.jsonl"
    write_jsonl(
        expected,
        [
            {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}},
            {"event_type": "assistant_message", "payload": {"text": "Summary:\n- one"}},
        ],
    )
    write_jsonl(
        actual,
        [
            {"event_type": "tool_call_request", "payload": {"tool_name": "bash"}},
            {"event_type": "assistant_message", "payload": {"text": "Short answer."}},
        ],
    )
    monkeypatch.setattr(sys, "argv", ["autonomos", "analyze-drift", str(expected), str(actual)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "tool_routing" in captured.out


def test_run_regression_prints_summary(monkeypatch, capsys, tmp_path: Path):
    class Result:
        passed = True
        example_id = "hello"
        actual_strategy = "simple_answer"
        actual_tool_family = "none"
        artifact_present = False
        expected_score = 0
        closest_match_example_id = "hello"
        closest_match_score = 0
        drift_summary = "No structured drift detected."
        primary_causes = []

    monkeypatch.setattr("autonomos.cli.run_regression_suite", lambda **kwargs: [Result()])
    monkeypatch.setattr("autonomos.cli.write_regression_report", lambda path, results: path)
    monkeypatch.setattr("autonomos.cli.write_regression_json", lambda path, results: path)
    monkeypatch.setattr(sys, "argv", ["autonomos", "run-regression"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "passed=1 total=1" in captured.out
    assert "PASS hello: strategy=simple_answer artifact=no expected_score=0 tool_family=none closest=hello score=0" in captured.out
