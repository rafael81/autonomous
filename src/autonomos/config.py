"""Configuration for live observation capture."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"


@dataclass(frozen=True)
class WebSocketAuthConfig:
    base_url: str
    api_key: str
    model: str
    provider: str
    account_id: str | None = None
    wire_api: str = "responses_websocket"
    env_key_name: str = "OPENAI_API_KEY"
    websocket_path: str = "/v1/responses"
    extra_headers: dict[str, str] = field(default_factory=dict)

    def headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers)
        return headers


def load_codex_auth_file(path: Path = CODEX_AUTH_PATH) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_ws_auth_config(env: dict[str, str] | None = None) -> WebSocketAuthConfig:
    source = env if env is not None else os.environ
    file_auth = load_codex_auth_file()

    api_key = source.get("OPENAI_API_KEY") or source.get("AUTONOMOS_ACCESS_TOKEN")
    account_id = source.get("AUTONOMOS_ACCOUNT_ID")
    if not api_key and file_auth:
        tokens = file_auth.get("tokens", {})
        api_key = tokens.get("access_token")
        account_id = account_id or tokens.get("account_id")
    if not api_key:
        raise ValueError("OPENAI_API_KEY or ~/.codex/auth.json access token is required for websocket capture")

    base_url = source.get("AUTONOMOS_WS_BASE_URL", "wss://api.openai.com/v1")
    model = source.get("AUTONOMOS_MODEL", "gpt-5")
    provider = source.get("AUTONOMOS_PROVIDER", "openai_ws")
    origin = source.get("AUTONOMOS_ORIGIN")
    version = source.get("AUTONOMOS_CLIENT_VERSION", "0.104.0")
    originator = source.get("AUTONOMOS_ORIGINATOR", "codex_cli_rs")

    extra_headers: dict[str, str] = {}
    if account_id:
        extra_headers["chatgpt-account-id"] = account_id
    if origin:
        extra_headers["Origin"] = origin
        extra_headers["Host"] = origin.removeprefix("https://").removeprefix("http://")
    if "chatgpt.com" in base_url:
        extra_headers.setdefault("Origin", "https://chatgpt.com")
        extra_headers.setdefault("Host", "chatgpt.com")
        extra_headers.setdefault("Accept", "*/*")
        extra_headers.setdefault("openai-beta", "responses_websockets=2026-02-06")
        extra_headers.setdefault("originator", originator)
        extra_headers.setdefault("version", version)

    return WebSocketAuthConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        provider=provider,
        account_id=account_id,
        extra_headers=extra_headers,
    )
