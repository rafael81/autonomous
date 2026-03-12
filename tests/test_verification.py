from pathlib import Path

from autonomos.verification import format_verification_results, verify_runtime_against_goldens


def test_verify_runtime_against_goldens_uses_run_chat(monkeypatch, tmp_path: Path):
    goldens = tmp_path / "goldens" / "roma-simple-hello"
    goldens.mkdir(parents=True)
    (goldens / "prompt.txt").write_text("say hello briefly\n", encoding="utf-8")
    (goldens / "meta.json").write_text('{"capture_mode":"golden_trace"}\n', encoding="utf-8")
    (goldens / "normalized.jsonl").write_text("", encoding="utf-8")

    class Summary:
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0
        strategy_id = "simple_answer"
        final_message = "hello"

    monkeypatch.setattr("autonomos.verification.run_chat", lambda **kwargs: Summary())

    results = verify_runtime_against_goldens(
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        goldens_dir=tmp_path / "goldens",
    )

    assert len(results) == 1
    assert results[0].matched_expected_golden is True


def test_verify_runtime_against_goldens_prefers_goldens_dir_for_comparison(monkeypatch, tmp_path: Path):
    goldens = tmp_path / "goldens" / "roma-simple-hello"
    goldens.mkdir(parents=True)
    (goldens / "prompt.txt").write_text("say hello briefly\n", encoding="utf-8")
    (goldens / "meta.json").write_text('{"capture_mode":"golden_trace"}\n', encoding="utf-8")
    (goldens / "normalized.jsonl").write_text("", encoding="utf-8")
    seen = {}

    class Summary:
        closest_match_example_id = "roma-simple-hello"
        closest_match_score = 0
        strategy_id = "simple_answer"
        final_message = "hello"

    def fake_run_chat(**kwargs):
        seen["baselines_dir"] = kwargs["baselines_dir"]
        return Summary()

    monkeypatch.setattr("autonomos.verification.run_chat", fake_run_chat)

    verify_runtime_against_goldens(
        profile="roma_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=tmp_path / "examples",
        memory_dir=tmp_path / "memory",
        goldens_dir=tmp_path / "goldens",
    )

    assert seen["baselines_dir"] == tmp_path / "goldens"


def test_format_verification_results_reports_match_state():
    rows = format_verification_results(
        [
            type(
                "Obj",
                (),
                {
                    "example_id": "roma-simple-hello",
                    "closest_match_example_id": "roma-simple-hello",
                    "closest_match_score": 0,
                    "strategy_id": "simple_answer",
                    "matched_expected_golden": True,
                },
            )()
        ]
    )

    assert rows == ["MATCH roma-simple-hello: closest=roma-simple-hello score=0 strategy=simple_answer"]
