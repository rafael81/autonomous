import json
from pathlib import Path

from autonomos.examples import build_examples_dataset
from autonomos.live_capture import run_capture


def test_build_examples_dataset_creates_ten_examples(tmp_path: Path):
    build_examples_dataset(tmp_path)
    example_dirs = sorted(path for path in tmp_path.iterdir() if path.is_dir())

    assert len(example_dirs) == 10
    for example_dir in example_dirs:
        for name in ("prompt.txt", "observed.jsonl", "normalized.jsonl", "report.md", "meta.json"):
            assert (example_dir / name).exists(), f"missing {name} in {example_dir.name}"


def test_generated_meta_contains_required_fields(tmp_path: Path):
    build_examples_dataset(tmp_path)
    meta = json.loads((tmp_path / "example-01-simple-short" / "meta.json").read_text(encoding="utf-8"))

    assert set(meta) >= {"example_id", "captured_at", "codex_source", "model", "capture_mode", "repro_command"}


def test_live_capture_wrapper_collects_stdout_and_stderr(tmp_path: Path):
    script = tmp_path / "emit.py"
    script.write_text("import sys; print('out'); print('err', file=sys.stderr)\n", encoding="utf-8")

    result = run_capture(["python3", str(script)])

    assert result.returncode == 0
    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"
