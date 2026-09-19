"""Qwen 2.5 7B local model facade."""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from backend.config import Settings
from backend.runtimes.base import LocalModelRuntime, choose_runtime, create_runtime


class QwenLocalModel:
    model_key = "qwen-local"
    display_name = "Qwen 2.5 7B"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._runtime: Optional[LocalModelRuntime] = None

    def _build_runtime(self) -> LocalModelRuntime:
        runtime_name = choose_runtime(self.settings.local_runtime)
        if not runtime_name:
            raise RuntimeError(
                "No local runtime available. Install llama-cpp-python, "
                "transformers+torch, or vllm."
            )
        return create_runtime(
            runtime_name,
            self.model_key,
            self.settings.qwen_model_path,
            model_id=self.settings.qwen_model_id,
            n_ctx=self.settings.qwen_context,
            n_threads=self.settings.resolve_threads(self.settings.qwen_threads),
            n_gpu_layers=self.settings.qwen_gpu_layers,
            hf_token=self.settings.hf_token or None,
        )

    @property
    def runtime(self) -> LocalModelRuntime:
        if self._runtime is None:
            self._runtime = self._build_runtime()
        return self._runtime

    async def load(self) -> None:
        await self.runtime.load()

    async def unload(self) -> None:
        if self._runtime:
            await self._runtime.unload()

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        return await self.runtime.generate(messages, **kwargs)

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        async for chunk in self.runtime.stream(messages, **kwargs):
            yield chunk

    async def health(self) -> dict[str, Any]:
        try:
            return await self.runtime.health()
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
