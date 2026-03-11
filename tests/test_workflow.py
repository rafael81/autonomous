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
        return LiveCaptureResult(
            command=command,
            returncode=0,
            stdout='{"timestamp":"2026-03-11T00:00:00Z","type":"thread.started","thread_id":"thread-1"}\n',
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
