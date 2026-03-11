from autonomos.codex_exec import build_exec_command, render_codex_config_toml
from autonomos.config import load_ws_auth_config


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
