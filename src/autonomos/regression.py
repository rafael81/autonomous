"""Golden evaluation suite and regression runner."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .app import ChatRunSummary, run_chat
from .compare import compare_normalized_sequences
from .io import read_jsonl
from .review import resolve_review_request


DEFAULT_EVAL_SUITE_PATH = Path("evals/golden_suite.json")


@dataclass(frozen=True)
class EvalCase:
    example_id: str
    prompt: str
    invocation_mode: str
    expected_strategy: str
    expected_tool_family: str
    max_score: int


@dataclass(frozen=True)
class RegressionResult:
    example_id: str
    prompt: str
    expected_strategy: str
    actual_strategy: str
    expected_tool_family: str
    actual_tool_family: str
    expected_score: int | None
    closest_match_example_id: str | None
    closest_match_score: int | None
    strategy_ok: bool
    tool_family_ok: bool
    score_ok: bool
    passed: bool
    final_message: str | None
    normalized_path: str | None
    session_dir: str


def load_eval_suite(path: Path = DEFAULT_EVAL_SUITE_PATH) -> list[EvalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**item) for item in payload]


def detect_tool_family(normalized_path: Path | None) -> str:
    if normalized_path is None or not normalized_path.exists():
        return "none"
    rows = read_jsonl(normalized_path)
    tool_names = [row.get("payload", {}).get("tool_name", "") for row in rows if row.get("event_type") == "tool_call_request"]
    if not tool_names:
        return "none"
    if any(name in {"list_dir", "read_file", "grep_text", "glob_paths", "search_files"} for name in tool_names):
        return "repo_inspection"
    if any(name == "bash" for name in tool_names):
        return "review"
    return "other"


def run_regression_suite(
    *,
    profile: str,
    cwd: Path,
    captures_dir: Path,
    promote_dir: Path,
    baselines_dir: Path,
    memory_dir: Path,
    goldens_dir: Path,
    suite_path: Path = DEFAULT_EVAL_SUITE_PATH,
) -> list[RegressionResult]:
    results: list[RegressionResult] = []
    for case in load_eval_suite(suite_path):
        prompt = case.prompt
        if case.invocation_mode == "review":
            prompt = resolve_review_request(cwd=cwd, instructions=case.prompt).prompt
        summary: ChatRunSummary = run_chat(
            prompt=prompt,
            profile=profile,
            cwd=cwd,
            captures_dir=captures_dir / case.example_id,
            promote_dir=promote_dir / case.example_id,
            baselines_dir=goldens_dir if goldens_dir.exists() else baselines_dir,
            memory_dir=memory_dir,
            session_id=f"regression-{case.example_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}",
        )
        actual_tool_family = detect_tool_family(summary.normalized_path)
        expected_score = _score_against_expected_golden(case.example_id, summary.normalized_path, goldens_dir)
        closest_score = summary.closest_match_score if summary.closest_match_score is not None else 10_000
        strategy_ok = summary.strategy_id == case.expected_strategy
        tool_family_ok = actual_tool_family == case.expected_tool_family
        score_ok = expected_score is not None and expected_score <= case.max_score
        results.append(
            RegressionResult(
                example_id=case.example_id,
                prompt=case.prompt,
                expected_strategy=case.expected_strategy,
                actual_strategy=summary.strategy_id,
                expected_tool_family=case.expected_tool_family,
                actual_tool_family=actual_tool_family,
                expected_score=expected_score,
                closest_match_example_id=summary.closest_match_example_id,
                closest_match_score=summary.closest_match_score,
                strategy_ok=strategy_ok,
                tool_family_ok=tool_family_ok,
                score_ok=score_ok,
                passed=strategy_ok and tool_family_ok and score_ok,
                final_message=summary.final_message,
                normalized_path=str(summary.normalized_path) if summary.normalized_path else None,
                session_dir=str(summary.session_dir),
            )
        )
    return results


def build_regression_report(results: list[RegressionResult]) -> str:
    passed = len([result for result in results if result.passed])
    lines = [
        "# Golden Regression Report",
        "",
        f"- passed: {passed}/{len(results)}",
        "",
        "## Results",
    ]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.extend(
            [
                f"### {status} {result.example_id}",
                f"- prompt: {result.prompt}",
                f"- strategy: expected={result.expected_strategy} actual={result.actual_strategy}",
                f"- tool_family: expected={result.expected_tool_family} actual={result.actual_tool_family}",
                f"- expected_golden_score: {result.expected_score if result.expected_score is not None else '?'}",
                f"- closest_match: {result.closest_match_example_id or 'none'} score={result.closest_match_score if result.closest_match_score is not None else '?'}",
                f"- session: {result.session_dir}",
                f"- normalized: {result.normalized_path or 'none'}",
                "",
            ]
        )
    return "\n".join(lines)


def write_regression_report(output_path: Path, results: list[RegressionResult]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_regression_report(results) + "\n", encoding="utf-8")
    return output_path


def write_regression_json(output_path: Path, results: list[RegressionResult]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _score_against_expected_golden(example_id: str, normalized_path: Path | None, goldens_dir: Path) -> int | None:
    if normalized_path is None or not normalized_path.exists():
        return None
    expected_path = goldens_dir / example_id / "normalized.jsonl"
    if not expected_path.exists():
        return None
    result = compare_normalized_sequences(read_jsonl(expected_path), read_jsonl(normalized_path))
    return result.score
