from unittest.mock import MagicMock, patch

from news_digest_bot.config import Source
from news_digest_bot.fetcher import extract_main_text, fetch_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title>新新聞</title><link>https://n.com/new</link>
<description>&lt;p&gt;今天的&lt;b&gt;新聞&lt;/b&gt;&lt;/p&gt;</description>
<pubDate>{now}</pubDate></item>
<item><title>舊新聞</title><link>https://n.com/old</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
</channel></rss>"""


def _resp(content):
    r = MagicMock()
    r.content = content
    r.raise_for_status = MagicMock()
    return r


def test_fetch_feed_filters_old_and_cleans_html():
    from email.utils import formatdate
    rss = RSS.replace("{now}", formatdate(usegmt=True)).encode()
    with patch("news_digest_bot.fetcher.requests.get", return_value=_resp(rss)):
        arts = fetch_feed(Source("測試", "https://n.com/rss", "科技"), lookback_hours=24, limit=10)
    assert [a.title for a in arts] == ["新新聞"]
    assert arts[0].summary == "今天的 新聞"
    assert arts[0].category_hint == "科技"


def test_fetch_feed_returns_empty_on_network_error():
    import requests
    with patch("news_digest_bot.fetcher.requests.get", side_effect=requests.ConnectionError("down")):
        assert fetch_feed(Source("x", "https://x"), 24, 10) == []


def test_extract_main_text_prefers_article_and_drops_noise():
    html = """<html><body><nav><p>這是導覽列的文字，應該要被移除掉才對</p></nav>
    <article><p>第一段：這是新聞的主要內容，長度足夠被保留下來。</p><p>分享</p>
    <p>第二段：更多的新聞細節描述，同樣應該被保留。</p></article>
    <script>alert(1)</script></body></html>"""
    text = extract_main_text(html)
    assert text.splitlines() == ["第一段：這是新聞的主要內容，長度足夠被保留下來。", "第二段：更多的新聞細節描述，同樣應該被保留。"]
