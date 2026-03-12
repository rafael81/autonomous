"""Review prompt helpers built around git diff targets."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewRequest:
    prompt: str
    user_facing_hint: str


def resolve_review_request(
    *,
    cwd: Path,
    base_branch: str | None = None,
    commit: str | None = None,
    instructions: str | None = None,
) -> ReviewRequest:
    if instructions:
        text = instructions.strip()
        if not text:
            raise ValueError("review instructions cannot be empty")
        return ReviewRequest(prompt=_with_review_context(cwd, text), user_facing_hint=text)

    if commit:
        title = _git(cwd, ["show", "--quiet", "--format=%s", commit]).strip()
        if title:
            return ReviewRequest(
                prompt=_with_review_context(
                    cwd,
                    f'Review the code changes introduced by commit {commit} ("{title}"). Provide prioritized, actionable findings.',
                    commit=commit,
                ),
                user_facing_hint=f"commit {commit[:7]}: {title}",
            )
        return ReviewRequest(
            prompt=_with_review_context(
                cwd,
                f"Review the code changes introduced by commit {commit}. Provide prioritized, actionable findings.",
                commit=commit,
            ),
            user_facing_hint=f"commit {commit[:7]}",
        )

    if base_branch:
        merge_base = _git(cwd, ["merge-base", "HEAD", base_branch]).strip()
        if merge_base:
            return ReviewRequest(
                prompt=_with_review_context(
                    cwd,
                    (
                        f"Review the code changes against the base branch '{base_branch}'. "
                        f"The merge base commit for this comparison is {merge_base}. "
                        f"Run `git diff {merge_base}` to inspect the changes relative to {base_branch}. "
                        "Provide prioritized, actionable findings."
                    ),
                    base_branch=base_branch,
                    merge_base=merge_base,
                ),
                user_facing_hint=f"changes against '{base_branch}'",
            )
        return ReviewRequest(
            prompt=_with_review_context(
                cwd,
                (
                    f"Review the code changes against the base branch '{base_branch}'. "
                    "Find the merge base and inspect the diff relative to that branch. "
                    "Provide prioritized, actionable findings."
                ),
                base_branch=base_branch,
            ),
            user_facing_hint=f"changes against '{base_branch}'",
        )

    return ReviewRequest(
        prompt=_with_review_context(
            cwd,
            "Review the current code changes (staged, unstaged, and untracked files) and provide prioritized findings.",
        ),
        user_facing_hint="current changes",
    )


def _git(cwd: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _with_review_context(
    cwd: Path,
    base_prompt: str,
    *,
    base_branch: str | None = None,
    merge_base: str | None = None,
    commit: str | None = None,
) -> str:
    sections = [base_prompt]
    status = _git(cwd, ["status", "--short"]).strip()
    if status:
        sections.append("Git status:\n" + status)

    diff_text = ""
    if commit:
        diff_text = _git(cwd, ["show", "--stat", "--patch", "--max-count=1", commit])
    elif base_branch and merge_base:
        diff_text = _git(cwd, ["diff", "--stat", "--patch", merge_base])
    else:
        diff_text = _git(cwd, ["diff", "--stat", "--patch", "HEAD"])
        if not diff_text:
            diff_text = _git(cwd, ["diff", "--stat", "--patch", "--cached"])

    trimmed = _trim_review_context(diff_text)
    if trimmed:
        sections.append("Diff excerpt:\n" + trimmed)
    return "\n\n".join(section for section in sections if section.strip())


def _trim_review_context(text: str, max_lines: int = 220, max_chars: int = 12000) -> str:
    if not text:
        return ""
    lines = text.splitlines()[:max_lines]
    joined = "\n".join(lines)
    return joined[:max_chars].rstrip()
