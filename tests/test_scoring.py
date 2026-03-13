from autonomos.regression import RegressionResult
from autonomos.scoring import compute_parity_score, format_parity_score


def _result(
    *,
    example_id: str,
    passed: bool,
    expected_score: int,
    strategy_ok: bool = True,
    tool_family_ok: bool = True,
    expected_artifact: str | None = None,
    artifact_present: bool = False,
    artifact_ok: bool = True,
) -> RegressionResult:
    return RegressionResult(
        example_id=example_id,
        prompt=example_id,
        expected_strategy="simple_answer",
        actual_strategy="simple_answer",
        expected_tool_family="none",
        actual_tool_family="none",
        expected_artifact=expected_artifact,
        artifact_present=artifact_present,
        expected_score=expected_score,
        allowed_max_score=0 if expected_score == 0 else 5,
        closest_match_example_id=example_id,
        closest_match_score=expected_score,
        strategy_ok=strategy_ok,
        tool_family_ok=tool_family_ok,
        artifact_ok=artifact_ok,
        score_ok=expected_score == 0,
        passed=passed,
        drift_summary="aligned" if expected_score == 0 else "drift",
        primary_causes=[],
        final_message="ok",
        normalized_path=None,
        session_dir="capture",
    )


def test_compute_parity_score_returns_ten_for_perfect_results():
    results = [
        _result(example_id="a", passed=True, expected_score=0),
        _result(example_id="b", passed=True, expected_score=0, expected_artifact="request_user_input", artifact_present=True),
    ]

    score = compute_parity_score(results)

    assert score.total_score == 10.0
    assert score.passed_cases == 2
    assert score.subscores["pass_rate"] == 4.0
    assert score.subscores["golden_closeness"] == 3.0


def test_compute_parity_score_penalizes_failed_and_drifting_results():
    results = [
        _result(example_id="a", passed=True, expected_score=1),
        _result(example_id="b", passed=False, expected_score=5, strategy_ok=False, tool_family_ok=False),
    ]

    score = compute_parity_score(results)

    assert score.total_score < 10.0
    assert score.passed_cases == 1
    assert score.subscores["strategy_accuracy"] < 1.5
    assert score.subscores["tool_accuracy"] < 1.0


def test_compute_parity_score_treats_within_allowed_threshold_as_full_closeness():
    results = [
        _result(example_id="review", passed=True, expected_score=5),
        _result(example_id="rui", passed=True, expected_score=5, expected_artifact="request_user_input", artifact_present=True),
    ]

    score = compute_parity_score(results)

    assert score.subscores["golden_closeness"] == 3.0


def test_format_parity_score_includes_component_lines():
    score = compute_parity_score([_result(example_id="a", passed=True, expected_score=0)])

    lines = format_parity_score(score)

    assert lines[0] == "score=10.0/10.0"
    assert any(line.startswith("pass_rate=") for line in lines)
    assert any(line.startswith("golden_closeness=") for line in lines)
