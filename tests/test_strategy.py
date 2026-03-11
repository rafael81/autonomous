from autonomos.instructions import build_full_instructions, render_user_request
from autonomos.policy import infer_prompt_policy
from autonomos.strategy import candidate_strategies, choose_strategy


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


def test_instruction_builders_embed_mode_and_request():
    decision = choose_strategy("Say hello briefly.")
    policy = infer_prompt_policy("Say hello briefly.", decision)
    instructions = build_full_instructions(decision, policy)
    request = render_user_request("Say hello briefly.")

    assert "Current mode: simple_answer." in instructions
    assert "concise, direct, friendly teammate tone" in instructions
    assert request.endswith("Say hello briefly.")


def test_candidate_strategies_returns_primary_then_fallbacks():
    decisions = candidate_strategies("Check the repository and verify the tests.")

    assert decisions[0].strategy_id == "tool_oriented"
    assert len(decisions) >= 2


def test_candidate_strategies_shortens_for_project_analysis():
    decisions = candidate_strategies("현재 내 프로젝트 분석")

    assert [decision.strategy_id for decision in decisions] == ["tool_oriented"]
