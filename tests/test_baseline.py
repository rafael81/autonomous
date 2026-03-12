import json
from pathlib import Path

from autonomos.baseline import (
    best_comparison_match,
    build_golden_registry,
    compare_capture_against_baselines,
    format_comparison_results,
    import_normalized_trace_as_example,
    promote_capture_to_example,
)
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


def test_import_normalized_trace_as_example_creates_golden_shape(tmp_path: Path):
    normalized_path = tmp_path / "trace.jsonl"
    rows = [
        {"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}},
    ]
    write_jsonl(normalized_path, rows)

    example_dir = import_normalized_trace_as_example(
        normalized_path=normalized_path,
        output_root=tmp_path / "goldens",
        example_id="codex-1",
        prompt="Analyze the repository.",
    )

    assert (example_dir / "prompt.txt").exists()
    assert (example_dir / "normalized.jsonl").exists()
    assert (example_dir / "observed.jsonl").exists()
    assert (example_dir / "meta.json").exists()
    assert (example_dir / "report.md").exists()
    meta = json.loads((example_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["capture_mode"] == "golden_trace"


def test_format_comparison_results_sorts_by_score():
    lines = format_comparison_results(
        [
            type("Obj", (), {"example_id": "b", "matches": False, "summary": "diff", "details": ["later"], "score": 3})(),
            type("Obj", (), {"example_id": "a", "matches": True, "summary": "matched", "details": [], "score": 0})(),
        ]
    )

    assert lines[0].startswith("MATCH a: score=0")


def test_build_golden_registry_reads_prompt_and_event_count(tmp_path: Path):
    example_dir = tmp_path / "goldens" / "codex-1"
    example_dir.mkdir(parents=True)
    (example_dir / "prompt.txt").write_text("hello\n", encoding="utf-8")
    write_jsonl(
        example_dir / "normalized.jsonl",
        [{"ts": "1", "source": "fixture", "channel": "x", "event_type": "session_start", "turn_id": None, "message_id": None, "call_id": None, "payload": {}, "raw": {}}],
    )
    (example_dir / "meta.json").write_text(json.dumps({"capture_mode": "golden_trace"}), encoding="utf-8")

    rows = build_golden_registry(tmp_path / "goldens")

    assert rows == [
        {
            "example_id": "codex-1",
            "prompt": "hello",
            "capture_mode": "golden_trace",
            "source_raw": None,
            "event_count": 1,
        }
    ]


def test_best_comparison_match_prefers_match_at_same_score():
    match = best_comparison_match(
        [
            type("Obj", (), {"example_id": "b", "matches": False, "summary": "", "details": [], "score": 1})(),
            type("Obj", (), {"example_id": "a", "matches": True, "summary": "", "details": [], "score": 1})(),
        ]
    )

    assert match is not None
    assert match.example_id == "a"
