import asyncio
from pathlib import Path

from textual.events import Key

from autonomos.app import ChatRunSummary
from autonomos.io import write_jsonl
from autonomos.tui_app import AutonomosTui, TuiConfig


def test_tui_submit_updates_transcript(monkeypatch, tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"event_type": "user_input", "payload": {"text": "hello"}},
            {"event_type": "assistant_message", "payload": {"text": "done"}},
        ],
    )
    summary = ChatRunSummary(
        final_message="done",
        strategy_id="simple_answer",
        baseline_example_id="codex-simple-hello",
        attempted_strategies=["simple_answer"],
        orchestration_summary="approval=no, request_user_input=no, retry=no",
        session_dir=tmp_path,
        normalized_path=normalized,
        promoted_example_dir=None,
        baseline_matches=1,
        baseline_total=10,
        comparison_summary_path=None,
        request_user_input_path=None,
        adaptive_notes="Attempt scores: [0]",
        memory_path=None,
        approval_request_path=None,
        closest_match_example_id="codex-simple-hello",
        closest_match_score=0,
        intended_match_example_id="codex-simple-hello",
        intended_match_score=0,
        drift_summary=None,
        drift_primary_causes=[],
        validation_hints=[],
        runtime_diagnostics=[],
    )
    monkeypatch.setattr("autonomos.tui_app.run_chat", lambda **kwargs: summary)

    app = AutonomosTui(
        TuiConfig(
            profile="roma_ws",
            cwd=Path("."),
            captures_dir=tmp_path / "captures",
            promote_dir=tmp_path / "examples_live",
            baselines_dir=tmp_path / "goldens",
            memory_dir=tmp_path / "memory",
            session_id="demo",
        )
    )

    async def run_scenario() -> None:
        async with app.run_test() as pilot:
            composer = app.query_one("#composer")
            composer.text = "hello"
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

    asyncio.run(run_scenario())

    assert app.state.last_summary is not None
    assert "assistant> done" in app.state.transcript_lines


def test_tui_composer_accepts_printable_ime_keys(tmp_path: Path):
    app = AutonomosTui(
        TuiConfig(
            profile="roma_ws",
            cwd=Path("."),
            captures_dir=tmp_path / "captures",
            promote_dir=tmp_path / "examples_live",
            baselines_dir=tmp_path / "goldens",
            memory_dir=tmp_path / "memory",
            session_id="demo",
        )
    )

    async def run_scenario() -> None:
        async with app.run_test() as _pilot:
            composer = app.query_one("#composer")
            await composer._on_key(Key("안", "안"))
            assert "안" in composer.text

    asyncio.run(run_scenario())
