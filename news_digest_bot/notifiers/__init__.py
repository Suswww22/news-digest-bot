from .base import Notifier
from .discord import DiscordNotifier
from .line import LineNotifier


def build_notifiers(channels: list[str]) -> list[Notifier]:
    registry = {"discord": DiscordNotifier, "line": LineNotifier}
    unknown = set(channels) - registry.keys()
    if unknown:
        raise ValueError(f"不支援的推播管道：{', '.join(sorted(unknown))}")
    return [registry[name].from_env() for name in channels]


__all__ = ["Notifier", "DiscordNotifier", "LineNotifier", "build_notifiers"]
