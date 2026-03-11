import sys

from autonomos import cli


def test_chat_direct_profile_requires_openai_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["autonomos", "chat", "hello", "--profile", "autonomos_direct"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "OPENAI_API_KEY is required for direct OpenAI API runtime" in captured.err
