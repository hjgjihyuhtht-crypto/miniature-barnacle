"""External provider base interface."""

from __future__ import annotations

import abc
from typing import Any, AsyncIterator, Optional


class ExternalProvider(abc.ABC):
    name: str = "base"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    @abc.abstractmethod
    async def generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...

    async def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "status": "configured" if self.configured else "not_configured",
        }
