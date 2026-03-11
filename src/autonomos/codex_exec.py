"""Helpers to prepare Codex live capture commands and config."""

from __future__ import annotations

from pathlib import Path

from .config import WebSocketAuthConfig


def render_codex_config_toml(auth: WebSocketAuthConfig) -> str:
    return "\n".join(
        [
            f"[model_providers.{auth.provider}]",
            f'base_url = "{auth.base_url}"',
            f'name = "{auth.provider}"',
            f'wire_api = "{auth.wire_api}"',
            f'env_key = "{auth.env_key_name}"',
            "",
            f"[profiles.{auth.provider}]",
            f'model = "{auth.model}"',
            f'model_provider = "{auth.provider}"',
            'model_reasoning_effort = "medium"',
            "",
        ]
    )


def build_exec_command(*, prompt: str, profile: str, cwd: Path | None = None, json_output: bool = True) -> list[str]:
    command = ["codex", "exec"]
    if profile:
        command.extend(["--profile", profile])
    if cwd:
        command.extend(["--cwd", str(cwd)])
    if json_output:
        command.append("--json")
    command.append(prompt)
    return command
