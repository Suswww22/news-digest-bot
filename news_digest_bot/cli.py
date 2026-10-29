"""指令列入口：python -m news_digest_bot [--dry-run]"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import load_config
from .fetcher import fetch_all
from .formatter import to_markdown
from .notifiers import build_notifiers
from .processing import SentStore, dedupe
from .site import build_site
from .summarizer import summarize

log = logging.getLogger("news_digest_bot")


def run(config_path: str, dry_run: bool, db_path: str, output_dir: str, site_dir: str = "site") -> int:
    cfg = load_config(config_path)
    store = SentStore(db_path)
    try:
        # 1. 爬取
        articles = fetch_all(cfg.sources, cfg.lookback_hours, cfg.max_articles_per_source,
                             cfg.fetch_full_text, cfg.max_chars_per_article)
        # 2. 資料處理
        articles = store.filter_new(dedupe(articles))
        log.info("去重並排除已推播後剩 %d 則", len(articles))
        if not articles:
            log.info("沒有新新聞，結束")
            return 0
        # 3. AI 摘要
        log.info("使用 %s 產生摘要", cfg.provider)
        digest = summarize(articles, provider=cfg.provider, model=cfg.model, max_items=cfg.max_items, language=cfg.language,
                           effort=cfg.effort, max_tokens=cfg.max_tokens)
        # 4. 輸出與推播
        out = Path(output_dir) / f"digest-{digest.date}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_markdown(digest), encoding="utf-8")
        log.info("摘要已存到 %s", out)
        index = build_site(digest, site_dir)
        log.info("網頁已產生：%s（用瀏覽器打開即可）", index.resolve())

        if dry_run:
            print(to_markdown(digest))
            return 0
        notifiers = build_notifiers(cfg.channels)
        if not notifiers:
            log.info("沒有設定任何推播管道的金鑰，只產生網頁")
        for notifier in notifiers:
            notifier.send(digest)
            log.info("已推播到 %s", notifier.name)
        store.mark_sent([it.url for it in digest.items])
        return 0
    finally:
        store.close()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="每日新聞摘要機器人")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("--dry-run", action="store_true", help="只印出摘要，不推播")
    p.add_argument("--db", default="data/sent.db")
    p.add_argument("--output", default="output")
    p.add_argument("--site", default="site", help="網頁輸出資料夾")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    raise SystemExit(run(args.config, args.dry_run, args.db, args.output, args.site))
