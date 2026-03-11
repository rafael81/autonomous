from pathlib import Path

from autonomos.io import read_jsonl, write_jsonl
from autonomos.live_capture import LiveCaptureResult
from autonomos.workflow import observe_prompt, slugify_prompt


def test_slugify_prompt_is_stable():
    assert slugify_prompt("Say hello briefly.") == "say-hello-briefly"


def test_observe_prompt_runs_end_to_end(tmp_path: Path):
    baselines = tmp_path / "examples"
    baseline_dir = baselines / "example-1"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": "thread-1", "message_id": None, "call_id": None, "payload": {}, "raw": {}},
            {"ts": "1", "source": "inferred", "channel": "exec", "event_type": "session_end", "turn_id": "thread-1", "message_id": None, "call_id": None, "payload": {}, "raw": {}},
        ],
    )

    def fake_runner(command: list[str], *, cwd: Path | None = None) -> LiveCaptureResult:
        prompt_text = command[-1]
        if "Preferred interaction archetype: simple_answer" in prompt_text:
            stdout = '{"timestamp":"2026-03-11T00:00:00Z","type":"thread.started","thread_id":"thread-1"}\n'
        else:
            stdout = (
                '{"timestamp":"2026-03-11T00:00:00Z","type":"thread.started","thread_id":"thread-1"}\n'
                '{"timestamp":"2026-03-11T00:00:01Z","type":"item.completed","item":{"id":"msg-1","details":{"type":"agent_message","text":"done"}}}\n'
            )
        return LiveCaptureResult(
            command=command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    outcome = observe_prompt(
        prompt="hello",
        profile="openai_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines,
        runner=fake_runner,
    )

    assert outcome.capture.normalized_path is not None
    assert outcome.promoted_example_dir is not None
    assert outcome.summary_path is not None
    assert outcome.summary_path.exists()
    assert len(outcome.comparison_results) == 1
    assert outcome.strategy.strategy_id == "simple_answer"
    assert outcome.attempted_strategies == ["simple_answer"]


def test_observe_prompt_can_fallback_to_second_strategy(tmp_path: Path):
    baselines = tmp_path / "examples"
    baseline_dir = baselines / "example-1"
    baseline_dir.mkdir(parents=True)
    write_jsonl(
        baseline_dir / "normalized.jsonl",
        [
            {"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": "thread-1", "message_id": None, "call_id": None, "payload": {}, "raw": {}},
            {"ts": "2", "source": "fixture", "channel": "x", "event_type": "assistant_message", "turn_id": "thread-1", "message_id": "m1", "call_id": None, "payload": {"text": "done"}, "raw": {}},
            {"ts": "3", "source": "inferred", "channel": "exec", "event_type": "session_end", "turn_id": "thread-1", "message_id": None, "call_id": None, "payload": {}, "raw": {}},
        ],
    )

    def fake_runner(command: list[str], *, cwd: Path | None = None) -> LiveCaptureResult:
        prompt_text = command[-1]
        if "Preferred interaction archetype: planning" in prompt_text:
            stdout = '{"timestamp":"2026-03-11T00:00:00Z","type":"thread.started","thread_id":"thread-1"}\n'
        else:
            stdout = (
                '{"timestamp":"2026-03-11T00:00:00Z","type":"thread.started","thread_id":"thread-1"}\n'
                '{"timestamp":"2026-03-11T00:00:01Z","type":"item.completed","item":{"id":"msg-1","details":{"type":"agent_message","text":"done"}}}\n'
            )
        return LiveCaptureResult(command=command, returncode=0, stdout=stdout, stderr="")

    outcome = observe_prompt(
        prompt="Make a plan for the migration",
        profile="openai_ws",
        cwd=tmp_path,
        captures_dir=tmp_path / "captures",
        promote_dir=tmp_path / "examples_live",
        baselines_dir=baselines,
        runner=fake_runner,
    )

    assert outcome.strategy.strategy_id == "tool_oriented"
    assert outcome.attempted_strategies == ["planning", "tool_oriented"]
