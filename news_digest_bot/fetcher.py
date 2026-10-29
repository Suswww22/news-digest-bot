"""爬蟲：用 RSS 取得新聞清單，再抓原文頁面萃取內文。"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import Source
from .models import Article

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/0.1; +https://github.com/Suswww22)"}
TIMEOUT = 15


def _parse_time(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)


def _clean_html(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def fetch_feed(source: Source, lookback_hours: int, limit: int) -> list[Article]:
    """解析單一 RSS，只保留時間窗內的新聞。"""
    try:
        resp = requests.get(source.url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("讀取 RSS 失敗 %s: %s", source.name, e)
        return []

    feed = feedparser.parse(resp.content)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    articles = []
    for entry in feed.entries:
        published = _parse_time(entry)
        if published and published < cutoff:
            continue
        link = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        articles.append(Article(
            source=source.name,
            title=title,
            url=link,
            published=published,
            summary=_clean_html(entry.get("summary", "")),
            category_hint=source.category_hint,
        ))
        if len(articles) >= limit:
            break
    log.info("%s：取得 %d 則", source.name, len(articles))
    return articles


def extract_main_text(html: str) -> str:
    """從新聞頁面萃取主要內文：優先 <article>，否則取段落最多的區塊。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    container = soup.find("article")
    if container is None:
        candidates = soup.find_all(["div", "section", "main"])
        container = max(candidates, key=lambda c: len(c.find_all("p", recursive=False)), default=soup)

    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    # 過濾太短的段落（多半是版權、分享按鈕文字）
    return "\n".join(p for p in paragraphs if len(p) >= 20)


def fetch_full_text(article: Article, max_chars: int) -> Article:
    try:
        resp = requests.get(article.url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        article.content = extract_main_text(resp.text)[:max_chars]
    except requests.RequestException as e:
        log.debug("抓取原文失敗 %s: %s", article.url, e)
    return article


def fetch_all(sources: list[Source], lookback_hours: int, limit: int,
              full_text: bool = True, max_chars: int = 2500) -> list[Article]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = pool.map(lambda s: fetch_feed(s, lookback_hours, limit), sources)
        articles = [a for batch in batches for a in batch]
        if full_text:
            articles = list(pool.map(lambda a: fetch_full_text(a, max_chars), articles))
    return articles
