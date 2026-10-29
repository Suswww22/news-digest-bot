from unittest.mock import patch

from news_digest_bot import cli


def test_run_end_to_end(tmp_path, articles, digest, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/webhook")
    cfg = tmp_path / "config.yaml"
    cfg.write_text("sources: [{name: x, url: https://x}]\nnotify: {channels: [discord]}\n", encoding="utf-8")
    db = tmp_path / "sent.db"

    with patch.object(cli, "fetch_all", return_value=articles), \
         patch.object(cli, "summarize", return_value=digest) as summ, \
         patch("news_digest_bot.notifiers.discord.DiscordNotifier.send") as send:
        assert cli.run(str(cfg), False, str(db), str(tmp_path / "out"), str(tmp_path / "site")) == 0
        assert send.call_count == 1
        assert (tmp_path / "out" / "digest-2026-10-29.md").exists()
        assert (tmp_path / "site" / "index.html").exists()

        # 第二次執行：已推播過的兩則會被排除，只剩一則送進摘要
        cli.run(str(cfg), False, str(db), str(tmp_path / "out"), str(tmp_path / "site"))
        assert [a.url for a in summ.call_args[0][0]] == ["https://b.com/2"]
