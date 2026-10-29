"""產生靜態網頁：最新一天的摘要放首頁，歷史摘要各自一頁，可直接部署到 GitHub Pages。"""
from __future__ import annotations

import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from .models import Digest, DigestItem

BADGES = {5: "重大", 4: "重要", 3: "關注", 2: "一般", 1: "一般"}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1d2129;--muted:#5f6b7a;--line:#e3e6eb;--accent:#2563eb;
--p5:#dc2626;--p4:#d97706;--p3:#2563eb;--p2:#6b7280}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#e6e8eb;--muted:#9aa4b2;
--line:#2a2f37;--accent:#60a5fa;--p5:#f87171;--p4:#fbbf24;--p3:#60a5fa;--p2:#9ca3af}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.7 "Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:32px 16px 64px}
header h1{margin:0;font-size:1.6rem}header .date{color:var(--muted);margin:4px 0 0}
.overview{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:10px;padding:14px 18px;margin:20px 0}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.filters button{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;
padding:4px 12px;font:inherit;font-size:.9rem;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
article h2{margin:0 0 6px;font-size:1.1rem;line-height:1.5}article h2 a{color:inherit;text-decoration:none}
article h2 a:hover{color:var(--accent)}article p{margin:8px 0 0}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;color:var(--muted);font-size:.85rem}
.badge{border-radius:6px;padding:0 8px;color:#fff;font-weight:600}
.p5{background:var(--p5)}.p4{background:var(--p4)}.p3{background:var(--p3)}.p2,.p1{background:var(--p2)}
.tag{border:1px solid var(--line);border-radius:6px;padding:0 8px}
nav.archive{margin-top:40px;border-top:1px solid var(--line);padding-top:16px}
nav.archive a{color:var(--accent);margin-right:12px;white-space:nowrap}
footer{margin-top:32px;color:var(--muted);font-size:.85rem}
"""

FILTER_JS = """
document.querySelectorAll('.filters button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.filters button').forEach(x=>x.setAttribute('aria-pressed',x===b));
  const c=b.dataset.cat;
  document.querySelectorAll('article').forEach(a=>{a.hidden=c!=='all'&&a.dataset.cat!==c});
}));
"""


def _item_html(it: DigestItem) -> str:
    level = min(max(it.importance, 1), 5)
    return f"""<article data-cat="{escape(it.category)}">
  <div class="meta"><span class="badge p{level}">{BADGES[level]}</span>
    <span class="tag">{escape(it.category)}</span><span>{escape(it.source)}</span></div>
  <h2><a href="{escape(it.url)}" target="_blank" rel="noopener">{escape(it.title)}</a></h2>
  <p>{escape(it.summary)}</p>
</article>"""


def render_page(digest: Digest, archive_dates: list[str], prefix: str = "") -> str:
    categories = sorted({it.category for it in digest.items})
    buttons = '<button data-cat="all" aria-pressed="true">全部</button>' + "".join(
        f'<button data-cat="{escape(c)}" aria-pressed="false">{escape(c)}</button>' for c in categories)
    archive = " ".join(f'<a href="{prefix}archive/{d}.html">{d}</a>' for d in archive_dates)
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日新聞摘要 {digest.date}</title><style>{CSS}</style></head>
<body><main>
<header><h1>📰 每日新聞摘要</h1><p class="date">{digest.date}</p></header>
<div class="overview">{escape(digest.overview)}</div>
<div class="filters">{buttons}</div>
{"".join(_item_html(it) for it in digest.items)}
<nav class="archive"><strong>歷史摘要：</strong> <a href="{prefix}index.html">最新</a> {archive}</nav>
<footer>由 news-digest-bot 自動產生：RSS 爬蟲 + LLM 摘要</footer>
</main><script>{FILTER_JS}</script></body></html>
"""


def load_digest(path: Path) -> Digest:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Digest(date=data["date"], overview=data["overview"],
                  items=[DigestItem(**it) for it in data["items"]])


def build_site(digest: Digest, site_dir: str | Path = "site") -> Path:
    """存下今天的 JSON，再用所有 JSON 重建首頁與歷史頁。"""
    site = Path(site_dir)
    data_dir = site / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / f"{digest.date}.json").write_text(
        json.dumps(asdict(digest), ensure_ascii=False, indent=2), encoding="utf-8")

    digests = sorted((load_digest(p) for p in data_dir.glob("*.json")), key=lambda d: d.date, reverse=True)
    dates = [d.date for d in digests]
    (site / "archive").mkdir(exist_ok=True)
    for d in digests:
        (site / "archive" / f"{d.date}.html").write_text(render_page(d, dates, prefix="../"), encoding="utf-8")
    index = site / "index.html"
    index.write_text(render_page(digests[0], dates), encoding="utf-8")
    return index
