"""Helpers to prepare Codex live capture commands and config."""

from __future__ import annotations

from pathlib import Path

from .config import load_openai_api_key
from .config import load_ws_auth_config
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


def build_provider_override_args(
    provider_name: str = "autonomos_ws",
    auth: WebSocketAuthConfig | None = None,
) -> list[str]:
    auth = auth or load_ws_auth_config()
    api_key = load_openai_api_key()
    base_url = "https://api.openai.com/v1"
    wire_api = "responses"
    args = [
        "-c",
        f'model_provider="{provider_name}"',
        "-c",
        f'model_providers.{provider_name}.name="{provider_name}"',
        "-c",
        f'model_providers.{provider_name}.base_url="{base_url}"',
        "-c",
        f'model_providers.{provider_name}.wire_api="{wire_api}"',
        "-c",
        f'model="{auth.model}"',
    ]
    args.extend(
        [
            "-c",
            f'model_providers.{provider_name}.experimental_bearer_token="{api_key}"',
        ]
    )
    return args


def build_exec_command(
    *,
    prompt: str,
    profile: str,
    cwd: Path | None = None,
    json_output: bool = True,
    strategy: StrategyDecision | None = None,
) -> list[str]:
    command = ["codex", "exec"]
    if profile and profile != "autonomos_direct":
        command.extend(["--profile", profile])
    else:
        command.extend(build_provider_override_args())
    if cwd:
        command.extend(["--cd", str(cwd)])
    if strategy:
        command.extend(["--sandbox", strategy.sandbox_mode])
        command.extend(["-c", f'model_reasoning_effort="{strategy.reasoning_effort}"'])
        if strategy.prefer_full_auto:
            command.append("--full-auto")
    if json_output:
        command.append("--json")
    command.append(prompt)
    return command
