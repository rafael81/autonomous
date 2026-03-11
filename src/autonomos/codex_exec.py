"""Helpers to prepare Codex live capture commands and config."""

from __future__ import annotations

from pathlib import Path

from .config import WebSocketAuthConfig
from .strategy import StrategyDecision


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


def describe_ws_runtime(auth: WebSocketAuthConfig) -> dict[str, object]:
    return {
        "base_url": auth.base_url,
        "websocket_path": auth.websocket_path,
        "provider": auth.provider,
        "model": auth.model,
        "account_id_present": bool(auth.account_id),
        "header_keys": sorted(auth.headers().keys()),
    }


def build_exec_command(
    *,
    prompt: str,
    profile: str,
    cwd: Path | None = None,
    json_output: bool = True,
    strategy: StrategyDecision | None = None,
) -> list[str]:
    command = ["codex", "exec"]
    if profile:
        command.extend(["--profile", profile])
    if cwd:
        command.extend(["--cwd", str(cwd)])
    if strategy:
        command.extend(["--sandbox", strategy.sandbox_mode])
        command.extend(["-c", f'model_reasoning_effort="{strategy.reasoning_effort}"'])
        if strategy.prefer_full_auto:
            command.append("--full-auto")
    if json_output:
        command.append("--json")
    command.append(prompt)
    return command
