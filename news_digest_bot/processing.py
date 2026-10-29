"""資料處理：網址正規化、去重、過濾已推播過的新聞。"""
from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Article

TRACKING_PARAMS = re.compile(r"^(utm_|fbclid$|gclid$|ref$|from$)")


def normalize_url(url: str) -> str:
    """去掉追蹤參數與結尾斜線，讓同一篇文章的不同連結視為相同。"""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _norm_title(title: str) -> str:
    return re.sub(r"[\W_]+", "", title.lower())


def dedupe(articles: list[Article], threshold: float = 0.85) -> list[Article]:
    """以網址與標題相似度去重，保留內文較完整的那篇。"""
    kept: list[Article] = []
    seen_urls: dict[str, int] = {}
    for art in articles:
        key = normalize_url(art.url)
        dup_idx = seen_urls.get(key)
        if dup_idx is None:
            t = _norm_title(art.title)
            dup_idx = next((i for i, k in enumerate(kept)
                            if SequenceMatcher(None, t, _norm_title(k.title)).ratio() >= threshold), None)
        if dup_idx is None:
            seen_urls[key] = len(kept)
            kept.append(art)
        elif len(art.text) > len(kept[dup_idx].text):
            kept[dup_idx] = art
    return kept


class SentStore:
    """用 SQLite 記錄推播過的網址，避免隔天重複推送同一則新聞。"""

    def __init__(self, path: str | Path = "data/sent.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS sent (url TEXT PRIMARY KEY, sent_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )

    def filter_new(self, articles: list[Article]) -> list[Article]:
        return [a for a in articles if not self.conn.execute(
            "SELECT 1 FROM sent WHERE url = ?", (normalize_url(a.url),)).fetchone()]

    def mark_sent(self, urls: list[str]) -> None:
        self.conn.executemany("INSERT OR IGNORE INTO sent (url) VALUES (?)",
                              [(normalize_url(u),) for u in urls])
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
