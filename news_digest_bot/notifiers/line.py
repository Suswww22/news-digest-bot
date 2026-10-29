from __future__ import annotations

import os

import requests

from ..formatter import to_plain_text
from ..models import Digest
from .base import Notifier, require_env

API = "https://api.line.me/v2/bot/message"
MAX_TEXT = 5000  # LINE 單則文字訊息上限


class LineNotifier(Notifier):
    """LINE Messaging API。有 LINE_TO 就 push 給指定對象，否則 broadcast 給所有好友。"""
    name = "line"

    def __init__(self, token: str, to: str | None = None, session: requests.Session | None = None):
        self.token = token
        self.to = to
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls) -> "LineNotifier":
        return cls(require_env("LINE_CHANNEL_ACCESS_TOKEN"), os.environ.get("LINE_TO") or None)

    def build_messages(self, digest: Digest) -> list[dict]:
        text = to_plain_text(digest)
        chunks = [text[i:i + MAX_TEXT] for i in range(0, len(text), MAX_TEXT)]
        return [{"type": "text", "text": c} for c in chunks[:5]]  # 一次最多 5 則

    def send(self, digest: Digest) -> None:
        body = {"messages": self.build_messages(digest)}
        endpoint = f"{API}/broadcast"
        if self.to:
            body["to"] = self.to
            endpoint = f"{API}/push"
        resp = self.session.post(endpoint, json=body, timeout=15,
                                 headers={"Authorization": f"Bearer {self.token}"})
        resp.raise_for_status()
