"""Configuration for live observation capture."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WebSocketAuthConfig:
    base_url: str
    api_key: str
    model: str
    provider: str
    wire_api: str = "responses_websocket"
    env_key_name: str = "OPENAI_API_KEY"

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }


def load_ws_auth_config(env: dict[str, str] | None = None) -> WebSocketAuthConfig:
    source = env if env is not None else os.environ
    api_key = source.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for websocket capture")

    base_url = source.get("AUTONOMOS_WS_BASE_URL", "wss://api.openai.com/v1")
    model = source.get("AUTONOMOS_MODEL", "gpt-5")
    provider = source.get("AUTONOMOS_PROVIDER", "openai_ws")
    return WebSocketAuthConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        provider=provider,
    )
