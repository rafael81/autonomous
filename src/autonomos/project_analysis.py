"""Deterministic evidence collection for project-analysis prompts."""

from __future__ import annotations

import subprocess
from pathlib import Path


def build_project_analysis_context(cwd: Path) -> str:
    sections: list[str] = []

    root_scan = _run(
        cwd,
        "pwd && rg --files -g 'README*' -g 'AGENTS.md' -g 'pyproject.toml' -g 'requirements*.txt' "
        "-g 'package.json' -g 'src/**' -g 'tests/**' | head -n 300",
    )
    if root_scan:
        sections.append("Initial scan:\n" + root_scan)

    for path in (
        "pyproject.toml",
        "README.md",
        "src/autonomos/cli.py",
        "src/autonomos/app.py",
        "src/autonomos/workflow.py",
        "src/autonomos/roma_runtime.py",
        "src/autonomos/strategy.py",
        "src/autonomos/policy.py",
        "src/autonomos/orchestration.py",
        "tests/test_cli.py",
        "tests/test_workflow.py",
    ):
        file_path = cwd / path
        if not file_path.exists():
            continue
        content = _run(cwd, f"sed -n '1,220p' {path}")
        if content:
            sections.append(f"{path}:\n{content}")

    pytest_output = _run(cwd, "./.venv/bin/pytest -q", timeout_ms=20000)
    if pytest_output:
        sections.append("Validation:\n" + pytest_output)
    else:
        fallback_pytest = _run(cwd, "python3 -m pytest -q", timeout_ms=20000)
        if fallback_pytest:
            sections.append("Validation:\n" + fallback_pytest)

    if not sections:
        return ""
    return "Observed project-analysis evidence:\n\n" + "\n\n".join(sections) + "\n\n"


def _run(cwd: Path, command: str, timeout_ms: int = 8000) -> str:
    completed = subprocess.run(
        ["/bin/zsh", "-lc", command],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_ms / 1000,
    )
    output = (completed.stdout or "").strip()
    if output:
        return output
    error = (completed.stderr or "").strip()
    return error[:800] if error else ""
