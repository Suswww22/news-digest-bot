import pytest

from news_digest_bot.config import load_config, resolve_provider


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ["LLM_PROVIDER", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_MODEL", "CLAUDE_MODEL"]:
        monkeypatch.delenv(key, raising=False)


def test_auto_picks_gemini_when_only_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    assert resolve_provider() == "gemini"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    assert resolve_provider() == "claude"


def test_env_overrides_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "Gemini")
    assert resolve_provider("claude") == "gemini"


def test_model_env_follows_provider(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("sources: []\nllm: {provider: gemini}\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("CLAUDE_MODEL", "should-not-be-used")
    c = load_config(cfg)
    assert (c.provider, c.model) == ("gemini", "gemini-2.5-pro")
