import json
from types import SimpleNamespace

import pytest

from news_digest_bot.summarizer import SummaryError, build_prompt, summarize


class FakeClient:
    def __init__(self, payload, stop_reason="end_turn"):
        self.calls = []
        text = json.dumps(payload, ensure_ascii=False)
        self.response = SimpleNamespace(
            stop_reason=stop_reason, stop_details=None,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


PAYLOAD = {"overview": "重點", "items": [
    {"article_id": 2, "title": "資安漏洞", "summary": "s", "category": "資安", "importance": 3},
    {"article_id": 0, "title": "台積電", "summary": "s", "category": "科技", "importance": 5},
    {"article_id": 99, "title": "幻覺", "summary": "s", "category": "x", "importance": 4},
]}


def test_summarize_maps_ids_sorts_and_drops_invalid(articles):
    client = FakeClient(PAYLOAD)
    digest = summarize(articles, model="claude-opus-5-5", client=client)
    assert [it.title for it in digest.items] == ["台積電", "資安漏洞"]
    assert digest.items[0].url == "https://a.com/1?utm_source=rss"
    assert digest.items[0].source == "中央社"

    call = client.calls[0]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["fallbacks"] == "default"


def test_summarize_respects_max_items(articles):
    digest = summarize(articles, model="m", max_items=1, client=FakeClient(PAYLOAD))
    assert len(digest.items) == 1


def test_summarize_raises_on_refusal(articles):
    with pytest.raises(SummaryError):
        summarize(articles, model="m", client=FakeClient(PAYLOAD, stop_reason="refusal"))


def test_summarize_empty_skips_api():
    client = FakeClient(PAYLOAD)
    assert summarize([], model="m", client=client).items == []
    assert client.calls == []


def test_prompt_uses_full_text_when_available(articles):
    prompt = build_prompt(articles, 5, "繁體中文")
    assert "完整內文" in prompt and "簡短描述" not in prompt
    assert '<article id="2"' in prompt


class FakeGemini:
    def __init__(self, payload, finish="STOP"):
        self.calls = []
        self.response = SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False) if payload else None,
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish))],
            usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=50),
        )
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_gemini_provider_uses_json_schema(articles):
    client = FakeGemini(PAYLOAD)
    digest = summarize(articles, provider="gemini", client=client)
    assert [it.title for it in digest.items] == ["台積電", "資安漏洞"]

    call = client.calls[0]
    assert call["model"] == "gemini-flash-latest"
    assert call["config"].response_mime_type == "application/json"
    importance = call["config"].response_json_schema["properties"]["items"]["items"]["properties"]["importance"]
    assert importance == {"type": "integer", "minimum": 1, "maximum": 5}


def test_gemini_truncated_output_raises(articles):
    with pytest.raises(SummaryError):
        summarize(articles, provider="gemini", client=FakeGemini(PAYLOAD, finish="MAX_TOKENS"))
    with pytest.raises(SummaryError):
        summarize(articles, provider="gemini", client=FakeGemini(None, finish="SAFETY"))


def test_unknown_provider(articles):
    with pytest.raises(ValueError):
        summarize(articles, provider="openai")
