from unittest.mock import MagicMock

import pytest

from news_digest_bot.formatter import to_markdown, to_plain_text
from news_digest_bot.notifiers import DiscordNotifier, LineNotifier, build_notifiers


def test_discord_payload(digest):
    session = MagicMock()
    DiscordNotifier("https://discord/webhook", session).send(digest)
    url, kwargs = session.post.call_args[0][0], session.post.call_args[1]
    assert url == "https://discord/webhook"
    embeds = kwargs["json"]["embeds"]
    assert embeds[0]["title"] == "台積電日本二廠" and embeds[0]["url"] == "https://a.com/1"
    assert "2026-10-29" in kwargs["json"]["content"]


def test_line_push_vs_broadcast(digest):
    session = MagicMock()
    LineNotifier("tok", to="U123", session=session).send(digest)
    assert session.post.call_args[0][0].endswith("/push")
    assert session.post.call_args[1]["json"]["to"] == "U123"
    assert session.post.call_args[1]["headers"]["Authorization"] == "Bearer tok"

    LineNotifier("tok", session=session).send(digest)
    assert session.post.call_args[0][0].endswith("/broadcast")


def test_channels_without_key_are_skipped(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert build_notifiers(["discord"]) == []
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/webhook")
    assert [n.name for n in build_notifiers(["discord"])] == ["discord"]
    with pytest.raises(ValueError):
        build_notifiers(["telegram"])


def test_formatters(digest):
    md = to_markdown(digest)
    assert md.startswith("# 📰 每日新聞摘要 2026-10-29") and "🔥 台積電日本二廠" in md
    assert "#" not in to_plain_text(digest)
