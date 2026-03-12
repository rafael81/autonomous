"""Promote captures into example datasets and compare against baselines."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from .compare import ComparisonResult, compare_normalized_sequences
from .io import read_jsonl
from .reports import build_report


@dataclass(frozen=True)
class BaselineComparison:
    example_id: str
    matches: bool
    summary: str
    details: list[str]
    score: int


def best_comparison_match(results: list[BaselineComparison]) -> BaselineComparison | None:
    if not results:
        return None
    return min(results, key=lambda item: (item.score, not item.matches, item.example_id))


def format_comparison_results(results: list[BaselineComparison], limit: int | None = None) -> list[str]:
    ordered = sorted(results, key=lambda item: (item.score, not item.matches, item.example_id))
    if limit is not None:
        ordered = ordered[:limit]
    lines: list[str] = []
    for result in ordered:
        status = "MATCH" if result.matches else "DIFF"
        line = f"{status} {result.example_id}: score={result.score} {result.summary}"
        if result.details:
            line += f" ({result.details[0]})"
        lines.append(line)
    return lines


def build_golden_registry(goldens_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for example_dir in sorted(path for path in goldens_root.iterdir() if path.is_dir()):
        meta_path = example_dir / "meta.json"
        prompt_path = example_dir / "prompt.txt"
        normalized_path = example_dir / "normalized.jsonl"
        meta: dict[str, object] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        prompt = prompt_path.read_text(encoding="utf-8").strip() if prompt_path.exists() else ""
        event_count = len(read_jsonl(normalized_path)) if normalized_path.exists() else 0
        rows.append(
            {
                "example_id": example_dir.name,
                "prompt": prompt,
                "capture_mode": meta.get("capture_mode", "unknown"),
                "source_raw": meta.get("source_raw"),
                "event_count": event_count,
            }
        )
    return rows


def find_examples_for_prompt(root: Path, prompt: str) -> list[str]:
    needle = prompt.strip()
    if not needle or not root.exists():
        return []
    matches: list[str] = []
    for example_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        prompt_path = example_dir / "prompt.txt"
        if not prompt_path.exists():
            continue
        candidate = prompt_path.read_text(encoding="utf-8").strip()
        if candidate == needle:
            matches.append(example_dir.name)
    return matches


def promote_capture_to_example(
    *,
    capture_dir: Path,
    output_root: Path,
    example_id: str,
    prompt: str | None = None,
) -> Path:
    example_dir = output_root / example_id
    example_dir.mkdir(parents=True, exist_ok=True)

    prompt_text = prompt
    prompt_path = capture_dir / "prompt.txt"
    if prompt_text is None and prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    prompt_text = prompt_text or ""

    normalized_path = capture_dir / "normalized.jsonl"
    stdout_path = capture_dir / "stdout.txt"
    stderr_path = capture_dir / "stderr.txt"
    meta_path = capture_dir / "meta.json"

    (example_dir / "prompt.txt").write_text(prompt_text + "\n", encoding="utf-8")
    if stdout_path.exists():
        shutil.copy2(stdout_path, example_dir / "observed.jsonl")
    if normalized_path.exists():
        shutil.copy2(normalized_path, example_dir / "normalized.jsonl")

    meta: dict = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(
        {
            "example_id": example_id,
            "promoted_from": str(capture_dir),
            "prompt": prompt_text,
            "capture_mode": meta.get("capture_mode", "live_capture"),
        }
    )
    (example_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    normalized = read_jsonl(example_dir / "normalized.jsonl") if (example_dir / "normalized.jsonl").exists() else []
    report = build_report(
        example_id=example_id,
        prompt=prompt_text,
        normalized_events=normalized,
        notes=f"Promoted from capture session {capture_dir.name}. stderr_exists={stderr_path.exists()}",
    )
    (example_dir / "report.md").write_text(report + "\n", encoding="utf-8")
    return example_dir


def import_normalized_trace_as_example(
    *,
    normalized_path: Path,
    output_root: Path,
    example_id: str,
    prompt: str,
    meta: dict | None = None,
) -> Path:
    example_dir = output_root / example_id
    example_dir.mkdir(parents=True, exist_ok=True)
    normalized = read_jsonl(normalized_path)
    (example_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    shutil.copy2(normalized_path, example_dir / "normalized.jsonl")
    (example_dir / "observed.jsonl").write_text(normalized_path.read_text(encoding="utf-8"), encoding="utf-8")
    payload = {
        "example_id": example_id,
        "prompt": prompt,
        "capture_mode": "golden_trace",
    }
    if meta:
        payload.update(meta)
    (example_dir / "meta.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (example_dir / "report.md").write_text(
        build_report(
            example_id=example_id,
            prompt=prompt,
            normalized_events=normalized,
            notes="Imported from a real normalized trace.",
        )
        + "\n",
        encoding="utf-8",
    )
    return example_dir


def compare_capture_against_baselines(
    *,
    normalized_path: Path,
    baselines_root: Path,
) -> list[BaselineComparison]:
    actual = read_jsonl(normalized_path)
    results: list[BaselineComparison] = []
    for example_dir in sorted(path for path in baselines_root.iterdir() if path.is_dir()):
        baseline_normalized = example_dir / "normalized.jsonl"
        if not baseline_normalized.exists():
            continue
        result: ComparisonResult = compare_normalized_sequences(read_jsonl(baseline_normalized), actual)
        results.append(
            BaselineComparison(
                example_id=example_dir.name,
                matches=result.matches,
                summary=result.summary,
                details=result.details,
                score=result.score,
            )
        )
    return results
