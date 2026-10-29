import logging
import os

from .base import Notifier
from .discord import DiscordNotifier
from .line import LineNotifier


def build_notifiers(channels: list[str]) -> list[Notifier]:
    registry = {"discord": DiscordNotifier, "line": LineNotifier}
    unknown = set(channels) - registry.keys()
    if unknown:
        raise ValueError(f"不支援的推播管道：{', '.join(sorted(unknown))}")
    # 沒設定金鑰的管道直接略過，讓只想看網頁的人不用申請 Webhook
    required = {"discord": "DISCORD_WEBHOOK_URL", "line": "LINE_CHANNEL_ACCESS_TOKEN"}
    active = []
    for name in channels:
        if not os.environ.get(required[name]):
            logging.getLogger(__name__).warning("略過 %s：未設定 %s", name, required[name])
            continue
        active.append(registry[name].from_env())
    return active


__all__ = ["Notifier", "DiscordNotifier", "LineNotifier", "build_notifiers"]
