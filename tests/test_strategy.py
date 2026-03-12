from pathlib import Path

from autonomos.instructions import build_full_instructions, render_user_request
from autonomos.policy import infer_prompt_policy
from autonomos.strategy import candidate_strategies, choose_strategy, infer_golden_strategy_hint


def test_choose_strategy_selects_planning():
    decision = choose_strategy("Make a plan for the migration.")

    assert decision.strategy_id == "planning"
    assert decision.baseline_example_id == "example-06-plan-only"
    assert decision.sandbox_mode == "read-only"


def test_choose_strategy_selects_tool_oriented():
    decision = choose_strategy("Check the repository and verify the tests.")

    assert decision.strategy_id == "tool_oriented"
    assert decision.prefer_full_auto is True


def test_choose_strategy_selects_tool_oriented_for_korean_structure_analysis():
    decision = choose_strategy("현재 프로젝트 구조 분석")

    assert decision.strategy_id == "tool_oriented"


def test_choose_strategy_selects_tool_oriented_for_review():
    decision = choose_strategy("Review only the current CLI changes.")

    assert decision.strategy_id == "tool_oriented"


def test_instruction_builders_embed_mode_and_request():
    decision = choose_strategy("Say hello briefly.")
    policy = infer_prompt_policy("Say hello briefly.", decision)
    instructions = build_full_instructions(decision, policy)
    request = render_user_request("Say hello briefly.")

    assert "Current mode: simple_answer." in instructions
    assert "## Planning" in instructions
    assert "## Validation" in instructions
    assert request.endswith("Say hello briefly.")


def test_candidate_strategies_returns_primary_then_fallbacks():
    decisions = candidate_strategies("Check the repository and verify the tests.")

    assert decisions[0].strategy_id == "tool_oriented"
    assert len(decisions) >= 2


def test_candidate_strategies_shortens_for_structure_like_analysis():
    decisions = candidate_strategies("현재 내 프로젝트 분석")

    assert [decision.strategy_id for decision in decisions] == ["tool_oriented"]


def test_candidate_strategies_shortens_for_structure_inspection():
    decisions = candidate_strategies("현재 프로젝트 구조 분석")

    assert [decision.strategy_id for decision in decisions] == ["tool_oriented"]


def test_infer_golden_strategy_hint_uses_matching_golden_prompt(tmp_path: Path):
    goldens = tmp_path / "goldens"
    hello = goldens / "roma-simple-hello"
    hello.mkdir(parents=True)
    (hello / "prompt.txt").write_text("say hello briefly\n", encoding="utf-8")

    decision = infer_golden_strategy_hint("say hello briefly please", goldens_root=goldens)

    assert decision is not None
    assert decision.strategy_id == "simple_answer"


def test_candidate_strategies_uses_golden_hint_for_ordering(tmp_path: Path):
    goldens = tmp_path / "goldens"
    review = goldens / "roma-readme-inspection"
    review.mkdir(parents=True)
    (review / "prompt.txt").write_text(
        "List the top-level files in this repository and then read the first 20 lines of README.md.\n",
        encoding="utf-8",
    )

    decisions = candidate_strategies(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        goldens_root=goldens,
    )

    assert decisions[0].strategy_id == "tool_oriented"
