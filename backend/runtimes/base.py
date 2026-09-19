"""Local model runtime abstractions."""

from __future__ import annotations

import abc
import logging
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger("nexus.runtimes")


class LocalModelRuntime(abc.ABC):
    name: str = "base"

    def __init__(self, model_key: str, model_path: str, **kwargs: Any):
        self.model_key = model_key
        self.model_path = model_path
        self.kwargs = kwargs
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    @abc.abstractmethod
    async def load(self) -> None: ...

    @abc.abstractmethod
    async def unload(self) -> None: ...

    @abc.abstractmethod
    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def stream(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> AsyncIterator[str]: ...

    @abc.abstractmethod
    async def health(self) -> dict[str, Any]: ...


def detect_available_runtimes() -> list[str]:
    available: list[str] = []
    try:
        import llama_cpp  # noqa: F401

        available.append("llama_cpp")
    except Exception:
        pass
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401

        available.append("transformers")
    except Exception:
        pass
    try:
        import vllm  # noqa: F401

        available.append("vllm")
    except Exception:
        pass
    return available


def choose_runtime(preferred: str = "auto") -> Optional[str]:
    available = detect_available_runtimes()
    if preferred and preferred != "auto":
        if preferred in available:
            return preferred
        logger.warning("Requested runtime %s not available; available=%s", preferred, available)
        return None
    # Prefer llama_cpp for GGUF, then transformers, then vllm
    for name in ("llama_cpp", "transformers", "vllm"):
        if name in available:
            return name
    return None


def create_runtime(
    runtime_name: str,
    model_key: str,
    model_path: str,
    **kwargs: Any,
) -> LocalModelRuntime:
    if runtime_name == "llama_cpp":
        from backend.runtimes.llama_cpp import LlamaCppRuntime

        return LlamaCppRuntime(model_key, model_path, **kwargs)
    if runtime_name == "transformers":
        from backend.runtimes.transformers import TransformersRuntime

        return TransformersRuntime(model_key, model_path, **kwargs)
    if runtime_name == "vllm":
        from backend.runtimes.vllm import VLLMRuntime

        return VLLMRuntime(model_key, model_path, **kwargs)
    raise ValueError(f"Unknown runtime: {runtime_name}")
