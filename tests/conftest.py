from datetime import datetime, timezone

import pytest

from news_digest_bot.models import Article, Digest, DigestItem


@pytest.fixture
def articles():
    now = datetime.now(timezone.utc)
    return [
        Article("中央社", "台積電宣布在日本設第二座廠", "https://a.com/1?utm_source=rss", now, "簡短描述", "完整內文" * 10, "科技"),
        Article("BBC", "OpenAI releases new model", "https://b.com/2", now, "desc", "", "AI"),
        Article("iThome", "資安漏洞影響數百萬台裝置", "https://c.com/3", now, "漏洞描述", "", "科技"),
    ]


@pytest.fixture
def digest():
    return Digest(date="2026-10-29", overview="今天的重點是半導體與 AI。", items=[
        DigestItem(0, "台積電日本二廠", "台積電宣布在熊本設立第二座廠。", "科技", 5, "https://a.com/1", "中央社"),
        DigestItem(2, "資安漏洞", "研究人員發現漏洞。", "資安", 3, "https://c.com/3", "iThome"),
    ])
