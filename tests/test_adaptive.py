from autonomos.adaptive import summarize_attempt_progress
from autonomos.baseline import BaselineComparison


def test_summarize_attempt_progress_detects_improvement():
    attempt_scores = [
        [BaselineComparison(example_id="a", matches=False, summary="x", details=["d"], score=3)],
        [BaselineComparison(example_id="a", matches=False, summary="x", details=["d"], score=1)],
    ]

    summary = summarize_attempt_progress(attempt_scores)

    assert summary.best_score == 1
    assert summary.improved is True
