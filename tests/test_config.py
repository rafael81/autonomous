import json

from autonomos.codex_exec import build_exec_command, describe_ws_runtime, render_codex_config_toml
from autonomos.config import load_codex_auth_file, load_ws_auth_config
from autonomos.strategy import choose_strategy


def test_load_ws_auth_config_from_env():
    config = load_ws_auth_config(
        {
            "OPENAI_API_KEY": "test-key",
            "AUTONOMOS_WS_BASE_URL": "wss://example.com/v1/",
            "AUTONOMOS_MODEL": "gpt-test",
            "AUTONOMOS_PROVIDER": "roma_ws",
        }
    )

    assert config.base_url == "wss://example.com/v1"
    assert config.model == "gpt-test"
    assert config.provider == "roma_ws"
    assert config.headers()["Authorization"] == "Bearer test-key"


def test_render_codex_config_toml_uses_provider_and_model():
    config = load_ws_auth_config({"OPENAI_API_KEY": "test-key"})
    text = render_codex_config_toml(config)

    assert "[model_providers.openai_ws]" in text
    assert 'model = "gpt-5"' in text


def test_build_exec_command_includes_json_and_profile():
    command = build_exec_command(prompt="hello", profile="openai_ws", json_output=True)

    assert command == ["codex", "exec", "--profile", "openai_ws", "--json", "hello"]


def test_build_exec_command_applies_strategy_runtime_policy():
    strategy = choose_strategy("Check the repository and verify the tests.")
    command = build_exec_command(prompt="hello", profile="openai_ws", json_output=True, strategy=strategy)

    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "--full-auto" in command


def test_build_exec_command_can_use_direct_provider_overrides(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    command = build_exec_command(prompt="hello", profile="autonomos_direct", json_output=True)

    assert command[0:2] == ["codex", "exec"]
    assert "--profile" not in command
    assert 'model_provider="autonomos_ws"' in command
    assert not any(".env_key=" in part for part in command)
    assert any("experimental_bearer_token" in part for part in command)


def test_load_codex_auth_file_reads_token_and_account(tmp_path):
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps({"tokens": {"access_token": "abc", "account_id": "acct"}}), encoding="utf-8")

    payload = load_codex_auth_file(auth_path)

    assert payload == {"tokens": {"access_token": "abc", "account_id": "acct"}}


def test_chatgpt_runtime_headers_match_roma_style():
    config = load_ws_auth_config(
        {
            "OPENAI_API_KEY": "test-key",
            "AUTONOMOS_ACCOUNT_ID": "acct-1",
            "AUTONOMOS_WS_BASE_URL": "wss://chatgpt.com/backend-api/codex",
        }
    )

    runtime = describe_ws_runtime(config)

    assert runtime["account_id_present"] is True
    assert "Authorization" in runtime["header_keys"]
    assert "chatgpt-account-id" in runtime["header_keys"]
    assert "openai-beta" in runtime["header_keys"]
