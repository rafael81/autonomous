from pathlib import Path

from autonomos.review import resolve_review_request


def test_resolve_review_request_defaults_to_uncommitted(tmp_path: Path):
    request = resolve_review_request(cwd=tmp_path)

    assert "Review the current code changes" in request.prompt
    assert request.user_facing_hint == "current changes"


def test_resolve_review_request_allows_custom_instructions(tmp_path: Path):
    request = resolve_review_request(cwd=tmp_path, instructions="Review only the CLI changes.")

    assert "Review only the CLI changes." in request.prompt
    assert request.user_facing_hint == "Review only the CLI changes."


def test_resolve_review_request_uses_base_branch_merge_base(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("autonomos.review._git", lambda cwd, args: "abc123\n" if args[:2] == ["merge-base", "HEAD"] else "")

    request = resolve_review_request(cwd=tmp_path, base_branch="main")

    assert "abc123" in request.prompt
    assert request.user_facing_hint == "changes against 'main'"


def test_resolve_review_request_includes_status_and_diff_context(monkeypatch, tmp_path: Path):
    def fake_git(cwd: Path, args: list[str]) -> str:
        if args[:2] == ["status", "--short"]:
            return " M src/autonomos/cli.py\n"
        if args[:2] == ["diff", "--stat"]:
            return " src/autonomos/cli.py | 2 +-\n"
        return ""

    monkeypatch.setattr("autonomos.review._git", fake_git)

    request = resolve_review_request(cwd=tmp_path)

    assert "Git status:" in request.prompt
    assert "Diff excerpt:" in request.prompt
