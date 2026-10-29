"""把摘要轉成各推播平台的訊息格式。"""
from __future__ import annotations

from .models import Digest

STARS = {5: "🔥", 4: "⭐", 3: "📌", 2: "▫️", 1: "▫️"}


def to_markdown(digest: Digest) -> str:
    lines = [f"# 📰 每日新聞摘要 {digest.date}", "", f"> {digest.overview}", ""]
    for i, it in enumerate(digest.items, 1):
        lines += [
            f"## {i}. {STARS.get(it.importance, '')} {it.title}",
            f"`{it.category}` · {it.source}",
            "",
            it.summary,
            "",
            f"🔗 {it.url}",
            "",
        ]
    return "\n".join(lines).strip() + "\n"


def to_plain_text(digest: Digest) -> str:
    """LINE 不支援 Markdown，用純文字排版。"""
    lines = [f"📰 每日新聞摘要 {digest.date}", digest.overview, ""]
    for i, it in enumerate(digest.items, 1):
        lines += [f"{i}. {STARS.get(it.importance, '')} 【{it.category}】{it.title}", it.summary, it.url, ""]
    return "\n".join(lines).strip()
