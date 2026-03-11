from autonomos.strategy import build_steered_prompt, candidate_strategies, choose_strategy


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


def test_build_steered_prompt_embeds_guidance():
    decision = choose_strategy("Say hello briefly.")
    text = build_steered_prompt("Say hello briefly.", decision)

    assert "Preferred interaction archetype" in text
    assert "User request:" in text
    assert "Say hello briefly." in text


def test_candidate_strategies_returns_primary_then_fallbacks():
    decisions = candidate_strategies("Check the repository and verify the tests.")

    assert decisions[0].strategy_id == "tool_oriented"
    assert len(decisions) >= 2


def test_candidate_strategies_shortens_for_project_analysis():
    decisions = candidate_strategies("현재 내 프로젝트 분석")

    assert [decision.strategy_id for decision in decisions] == ["tool_oriented"]
