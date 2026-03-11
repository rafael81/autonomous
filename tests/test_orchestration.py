from autonomos.baseline import BaselineComparison
from autonomos.orchestration import decide_orchestration
from autonomos.strategy import choose_strategy


def test_orchestration_requests_user_input_when_prompt_implies_choice():
    strategy = choose_strategy("Choose the better direction for this plan.")
    decision = decide_orchestration(
        strategy=strategy,
        comparison_results=[],
        has_normalized_output=True,
        prompt="Choose the better direction for this plan.",
    )

    assert decision.should_request_user_input is True


def test_orchestration_retries_on_high_mismatch():
    strategy = choose_strategy("Check the repository and verify the tests.")
    decision = decide_orchestration(
        strategy=strategy,
        comparison_results=[
            BaselineComparison(
                example_id="example-1",
                matches=False,
                summary="diff",
                details=["a", "b", "c"],
                score=3,
            )
        ],
        has_normalized_output=True,
        prompt="Check the repository and verify the tests.",
    )

    assert decision.should_retry is True
    assert decision.retry_reason == "baseline mismatch remains high"
