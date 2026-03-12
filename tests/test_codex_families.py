import json
from pathlib import Path

from autonomos.codex_families import CodexPromptFamily, build_codex_capture_command, get_core_prompt_family, load_core_prompt_families


def test_load_core_prompt_families_reads_entries(tmp_path: Path):
    payload = [
        {
            "family_id": "hello",
            "prompt": "say hello briefly",
            "invocation_mode": "chat",
            "expected_strategy": "simple_answer",
            "expected_tool_family": "none",
            "max_score": 0,
            "expected_artifact": None,
            "notes": "demo",
        }
    ]
    path = tmp_path / "families.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    families = load_core_prompt_families(path)

    assert len(families) == 1
    assert families[0].family_id == "hello"


def test_get_core_prompt_family_raises_for_unknown(tmp_path: Path):
    path = tmp_path / "families.json"
    path.write_text("[]", encoding="utf-8")

    try:
        get_core_prompt_family("missing", path=path)
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_build_codex_capture_command_uses_review_subcommand():
    family = CodexPromptFamily(
        family_id="review-demo",
        prompt="Review the current code changes and provide prioritized findings.",
        invocation_mode="review",
        expected_strategy="planning",
        expected_tool_family="review",
        max_score=5,
    )

    command = build_codex_capture_command(family)

    assert command[:3] == ["codex", "exec", "review"]
    assert "--uncommitted" in command
