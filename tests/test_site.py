from dataclasses import replace

from news_digest_bot.models import DigestItem
from news_digest_bot.site import build_site


def test_build_site_writes_index_and_archive(tmp_path, digest):
    older = replace(digest, date="2026-10-28", overview="昨天的重點",
                    items=[DigestItem(1, "<script>x</script>", "摘要", "AI", 4, "https://b.com/2", "BBC")])
    build_site(older, tmp_path)
    index = build_site(digest, tmp_path)

    html = index.read_text(encoding="utf-8")
    assert "2026-10-29" in html and "台積電日本二廠" in html      # 首頁是最新一天
    assert 'href="archive/2026-10-28.html"' in html
    assert 'data-cat="資安"' in html                             # 分類篩選按鈕

    old = (tmp_path / "archive" / "2026-10-28.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in old and "<script>x" not in old  # 標題有跳脫，避免 XSS
    assert 'href="../index.html"' in old
    assert sorted(p.name for p in (tmp_path / "data").iterdir()) == ["2026-10-28.json", "2026-10-29.json"]
