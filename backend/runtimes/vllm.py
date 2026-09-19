"""vLLM runtime (GPU-oriented)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from backend.runtimes.base import LocalModelRuntime

logger = logging.getLogger("nexus.runtimes.vllm")


class VLLMRuntime(LocalModelRuntime):
    name = "vllm"

    def __init__(self, model_key: str, model_path: str, **kwargs: Any):
        super().__init__(model_key, model_path, **kwargs)
        self._engine = None
        self.model_id = kwargs.get("model_id") or model_path
        self.hf_token = kwargs.get("hf_token") or None

    def _resolve_source(self) -> str:
        path = Path(self.model_path)
        if path.exists() and path.is_dir() and any(path.iterdir()):
            return str(path)
        return str(self.model_id)

    async def load(self) -> None:
        if self._loaded:
            return

        def _load() -> None:
            from vllm import LLM

            self._engine = LLM(model=self._resolve_source())

        await asyncio.to_thread(_load)
        self._loaded = True
        logger.info("Loaded vLLM model for %s", self.model_key)

    async def unload(self) -> None:
        self._engine = None
        self._loaded = False

    def _prompt(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for m in messages:
            parts.append(f"{m.get('role', 'user')}: {m.get('content', '')}")
        parts.append("assistant:")
        return "\n".join(parts)

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        if not self._loaded:
            await self.load()
        max_tokens = int(kwargs.get("max_tokens", 2048))
        temperature = float(kwargs.get("temperature", 0.7))

        def _gen() -> dict[str, Any]:
            from vllm import SamplingParams

            assert self._engine is not None
            params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
            outputs = self._engine.generate([self._prompt(messages)], params)
            text = outputs[0].outputs[0].text
            return {"content": text, "usage": {}}

        return await asyncio.to_thread(_gen)

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        # vLLM offline LLM API: generate then yield (streaming requires AsyncLLMEngine)
        result = await self.generate(messages, **kwargs)
        yield result["content"]

    async def health(self) -> dict[str, Any]:
        return {
            "runtime": self.name,
            "loaded": self._loaded,
            "source": self._resolve_source(),
        }
