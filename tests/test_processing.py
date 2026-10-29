from news_digest_bot.models import Article
from news_digest_bot.processing import SentStore, dedupe, normalize_url


def test_normalize_url_strips_tracking_and_slash():
    assert normalize_url("HTTPS://News.com/a/?utm_source=x&id=3&fbclid=y") == "https://news.com/a?id=3"


def test_dedupe_by_url_keeps_longer_text():
    a = Article("s", "標題一", "https://x.com/a?utm_medium=rss", summary="短")
    b = Article("s", "完全不同的標題", "https://x.com/a/", content="比較長的內文" * 5)
    result = dedupe([a, b])
    assert len(result) == 1 and result[0] is b


def test_dedupe_by_similar_title():
    a = Article("中央社", "台積電宣布赴日設第二座廠", "https://a.com/1")
    b = Article("BBC", "台積電宣布赴日設第二座廠！", "https://b.com/9")
    c = Article("BBC", "颱風明天登陸", "https://b.com/10")
    assert [x.url for x in dedupe([a, b, c])] == ["https://a.com/1", "https://b.com/10"]


def test_sent_store_filters_previously_sent(tmp_path, articles):
    store = SentStore(tmp_path / "sent.db")
    store.mark_sent(["https://a.com/1"])  # 不帶追蹤參數也要能比對到
    assert [a.url for a in store.filter_new(articles)] == ["https://b.com/2", "https://c.com/3"]
    store.close()
