from __future__ import annotations

import os
from abc import ABC, abstractmethod

from ..models import Digest


class Notifier(ABC):
    name = "base"

    @abstractmethod
    def send(self, digest: Digest) -> None: ...


def require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"缺少環境變數 {key}，請參考 .env.example 設定")
    return value
