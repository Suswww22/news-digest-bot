from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Source:
    name: str
    url: str
    category_hint: str = ""


@dataclass
class Config:
    sources: list[Source]
    lookback_hours: int = 24
    max_articles_per_source: int = 8
    max_items: int = 10
    fetch_full_text: bool = True
    max_chars_per_article: int = 2500
    language: str = "繁體中文"
    provider: str = "claude"
    model: str | None = None
    effort: str = "low"
    max_tokens: int = 16000
    channels: list[str] = field(default_factory=lambda: ["discord"])


def load_config(path: str | Path = "config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    digest = raw.get("digest", {})
    llm = raw.get("llm", {})
    notify = raw.get("notify", {})
    provider = resolve_provider(llm.get("provider", "auto"))
    return Config(
        sources=[Source(**s) for s in raw.get("sources", [])],
        lookback_hours=digest.get("lookback_hours", 24),
        max_articles_per_source=digest.get("max_articles_per_source", 8),
        max_items=digest.get("max_items", 10),
        fetch_full_text=digest.get("fetch_full_text", True),
        max_chars_per_article=digest.get("max_chars_per_article", 2500),
        language=digest.get("language", "繁體中文"),
        provider=provider,
        # 金鑰一律從環境變數讀取，不寫進設定檔
        model=os.environ.get(f"{provider.upper()}_MODEL") or llm.get("model"),
        effort=llm.get("effort", "low"),
        max_tokens=llm.get("max_tokens", 16000),
        channels=notify.get("channels", ["discord"]),
    )


def resolve_provider(configured: str = "auto") -> str:
    """LLM_PROVIDER 環境變數優先；auto 時看哪一把金鑰有設定。"""
    choice = (os.environ.get("LLM_PROVIDER") or configured or "auto").lower()
    if choice != "auto":
        return choice
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        return "gemini"
    return "claude"
