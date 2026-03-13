"""User-facing Codex parity scoring built on regression results."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .regression import RegressionResult


@dataclass(frozen=True)
class ParityScore:
    total_score: float
    max_score: float
    summary: str
    passed_cases: int
    total_cases: int
    subscores: dict[str, float]
    weights: dict[str, float]


_WEIGHTS = {
    "pass_rate": 4.0,
    "golden_closeness": 3.0,
    "strategy_accuracy": 1.5,
    "tool_accuracy": 1.0,
    "artifact_accuracy": 0.5,
}


def compute_parity_score(results: list[RegressionResult]) -> ParityScore:
    if not results:
        return ParityScore(
            total_score=0.0,
            max_score=10.0,
            summary="No regression results were available, so the Codex parity score is 0.0/10.",
            passed_cases=0,
            total_cases=0,
            subscores={key: 0.0 for key in _WEIGHTS},
            weights=dict(_WEIGHTS),
        )

    total_cases = len(results)
    passed_cases = len([result for result in results if result.passed])
    pass_rate = passed_cases / total_cases
    strategy_accuracy = len([result for result in results if result.strategy_ok]) / total_cases
    tool_accuracy = len([result for result in results if result.tool_family_ok]) / total_cases

    artifact_expected = [result for result in results if result.expected_artifact is not None]
    artifact_accuracy = (
        len([result for result in artifact_expected if result.artifact_ok]) / len(artifact_expected)
        if artifact_expected
        else 1.0
    )

    golden_closeness = _golden_closeness(results)
    subscores = {
        "pass_rate": round(pass_rate * _WEIGHTS["pass_rate"], 2),
        "golden_closeness": round(golden_closeness * _WEIGHTS["golden_closeness"], 2),
        "strategy_accuracy": round(strategy_accuracy * _WEIGHTS["strategy_accuracy"], 2),
        "tool_accuracy": round(tool_accuracy * _WEIGHTS["tool_accuracy"], 2),
        "artifact_accuracy": round(artifact_accuracy * _WEIGHTS["artifact_accuracy"], 2),
    }
    total_score = round(sum(subscores.values()), 2)
    summary = (
        f"Autonomos currently scores {total_score}/10 against the Codex parity suite "
        f"({passed_cases}/{total_cases} regression cases passing)."
    )
    return ParityScore(
        total_score=total_score,
        max_score=10.0,
        summary=summary,
        passed_cases=passed_cases,
        total_cases=total_cases,
        subscores=subscores,
        weights=dict(_WEIGHTS),
    )


def format_parity_score(score: ParityScore) -> list[str]:
    return [
        f"score={score.total_score}/{score.max_score}",
        f"summary={score.summary}",
        f"passed={score.passed_cases}/{score.total_cases}",
        *[
            f"{name}={value}/{score.weights[name]}"
            for name, value in score.subscores.items()
        ],
    ]


def parity_score_as_dict(score: ParityScore) -> dict[str, object]:
    return asdict(score)


def _golden_closeness(results: list[RegressionResult]) -> float:
    values: list[float] = []
    for result in results:
        if result.expected_score is None:
            values.append(0.0)
            continue
        threshold = max(result.allowed_max_score, 0)
        if result.expected_score <= threshold:
            values.append(1.0)
            continue
        remaining_headroom = max(1, 5 - threshold)
        overage = min(result.expected_score - threshold, remaining_headroom)
        values.append(max(0.0, 1 - (overage / remaining_headroom)))
    return sum(values) / len(values)
