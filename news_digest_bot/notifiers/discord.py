from __future__ import annotations

import requests

from ..models import Digest
from .base import Notifier, require_env

COLORS = {5: 0xE74C3C, 4: 0xF39C12, 3: 0x3498DB}
MAX_EMBEDS = 10  # Discord 單則訊息最多 10 個 embed


class DiscordNotifier(Notifier):
    name = "discord"

    def __init__(self, webhook_url: str, session: requests.Session | None = None):
        self.webhook_url = webhook_url
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls) -> "DiscordNotifier":
        return cls(require_env("DISCORD_WEBHOOK_URL"))

    def build_payload(self, digest: Digest) -> dict:
        embeds = [{
            "title": it.title[:256],
            "url": it.url,
            "description": it.summary[:4096],
            "color": COLORS.get(it.importance, 0x95A5A6),
            "footer": {"text": f"{it.category} · {it.source}"},
        } for it in digest.items[:MAX_EMBEDS]]
        return {"content": f"**📰 每日新聞摘要 {digest.date}**\n{digest.overview}"[:2000], "embeds": embeds}

    def send(self, digest: Digest) -> None:
        resp = self.session.post(self.webhook_url, json=self.build_payload(digest), timeout=15)
        resp.raise_for_status()
