import json
from pathlib import Path

from autonomos.baseline import compare_capture_against_baselines, promote_capture_to_example
from autonomos.io import write_jsonl


def test_promote_capture_to_example_creates_example_shape(tmp_path: Path):
    capture_dir = tmp_path / "capture" / "session-1"
    capture_dir.mkdir(parents=True)
    (capture_dir / "prompt.txt").write_text("hello\n", encoding="utf-8")
    (capture_dir / "stdout.txt").write_text("stdout\n", encoding="utf-8")
    (capture_dir / "stderr.txt").write_text("", encoding="utf-8")
    write_jsonl(
        capture_dir / "normalized.jsonl",
        [{"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}}],
    )
    (capture_dir / "meta.json").write_text(json.dumps({"capture_mode": "live_capture"}), encoding="utf-8")

    example_dir = promote_capture_to_example(capture_dir=capture_dir, output_root=tmp_path / "examples_live", example_id="live-1")

    assert (example_dir / "prompt.txt").exists()
    assert (example_dir / "observed.jsonl").exists()
    assert (example_dir / "normalized.jsonl").exists()
    assert (example_dir / "meta.json").exists()
    assert (example_dir / "report.md").exists()


def test_compare_capture_against_baselines_finds_match(tmp_path: Path):
    baselines_root = tmp_path / "examples"
    capture_path = tmp_path / "normalized.jsonl"
    baseline_dir = baselines_root / "example-1"
    baseline_dir.mkdir(parents=True)
    rows = [
        {"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
        {"ts": "2", "source": "fixture", "channel": "x", "event_type": "assistant_message", "turn_id": None, "message_id": "m1", "call_id": None, "payload": {"text": "hi"}, "raw": {}},
    ]
    write_jsonl(baseline_dir / "normalized.jsonl", rows)
    write_jsonl(capture_path, rows)

    results = compare_capture_against_baselines(normalized_path=capture_path, baselines_root=baselines_root)

    assert len(results) == 1
    assert results[0].matches is True
