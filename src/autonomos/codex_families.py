"""Core Codex prompt-family definitions and capture helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CORE_PROMPT_FAMILIES_PATH = Path("evals/core_prompt_families.json")


@dataclass(frozen=True)
class CodexPromptFamily:
    family_id: str
    prompt: str
    invocation_mode: str
    expected_strategy: str
    expected_tool_family: str
    max_score: int
    expected_artifact: str | None = None
    notes: str = ""


def load_core_prompt_families(path: Path = DEFAULT_CORE_PROMPT_FAMILIES_PATH) -> list[CodexPromptFamily]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [CodexPromptFamily(**item) for item in payload]


def get_core_prompt_family(
    family_id: str,
    *,
    path: Path = DEFAULT_CORE_PROMPT_FAMILIES_PATH,
) -> CodexPromptFamily:
    for family in load_core_prompt_families(path):
        if family.family_id == family_id:
            return family
    raise KeyError(f"unknown Codex prompt family: {family_id}")


def build_codex_capture_command(family: CodexPromptFamily) -> list[str]:
    if family.invocation_mode == "review":
        return [
            "codex",
            "exec",
            "review",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "--uncommitted",
        ]

    return [
        "codex",
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        family.prompt,
    ]


def build_codex_capture_metadata(family: CodexPromptFamily, command: list[str]) -> dict[str, object]:
    return {
        "prompt_family": family.family_id,
        "invocation_mode": family.invocation_mode,
        "expected_strategy": family.expected_strategy,
        "expected_tool_family": family.expected_tool_family,
        "expected_artifact": family.expected_artifact,
        "capture_command": command,
        "capture_mode": "codex_exec",
    }
