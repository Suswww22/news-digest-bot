from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    source: str
    title: str
    url: str
    published: datetime | None = None
    summary: str = ""          # RSS 提供的簡短描述
    content: str = ""          # 爬取原文後的內文
    category_hint: str = ""

    @property
    def text(self) -> str:
        """給 LLM 的內文：優先用爬到的全文，否則退回 RSS 摘要。"""
        return self.content or self.summary


@dataclass
class DigestItem:
    article_id: int
    title: str
    summary: str
    category: str
    importance: int
    url: str = ""
    source: str = ""


@dataclass
class Digest:
    date: str
    overview: str
    items: list[DigestItem] = field(default_factory=list)
