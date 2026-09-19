"""Model manager — load/unload/status for local models."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from backend.config import Settings, get_settings
from backend.local_models.llama import LlamaLocalModel
from backend.local_models.qwen import QwenLocalModel
from backend.providers.claude import ClaudeProvider
from backend.providers.gemini import GeminiProvider
from backend.providers.openai import OpenAIProvider
from backend.providers.openrouter import OpenRouterProvider
from backend.runtimes.base import detect_available_runtimes

logger = logging.getLogger("nexus.model_manager")


def _model_files_present(path: str) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    if p.is_file():
        return True
    return any(p.rglob("*"))


class ModelManager:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.llama = LlamaLocalModel(self.settings)
        self.qwen = QwenLocalModel(self.settings)
        # OpenRouter (when set) is the single gateway for all external API models
        self.openrouter = OpenRouterProvider(self.settings.openrouter_api_key)
        if self.openrouter.configured:
            self.openai = OpenRouterProvider(self.settings.openrouter_api_key, name="openai")
            self.gemini = OpenRouterProvider(self.settings.openrouter_api_key, name="gemini")
            self.claude = OpenRouterProvider(self.settings.openrouter_api_key, name="claude")
            logger.info("External APIs routed via OpenRouter")
        else:
            self.openai = OpenAIProvider(self.settings.openai_api_key)
            self.gemini = GeminiProvider(self.settings.gemini_api_key)
            self.claude = ClaudeProvider(self.settings.anthropic_api_key)
        self._loaded: list[str] = []
        self._lock = asyncio.Lock()

    async def ensure_loaded(self, model_key: str) -> None:
        if model_key not in ("llama-local", "qwen-local"):
            return
        async with self._lock:
            if model_key in self._loaded:
                return
            while len(self._loaded) >= self.settings.model_max_loaded:
                victim = self._loaded.pop(0)
                await self._unload(victim)
            await self._load(model_key)
            self._loaded.append(model_key)

    async def _load(self, model_key: str) -> None:
        logger.info("Loading model %s", model_key)
        if model_key == "llama-local":
            await self.llama.load()
        elif model_key == "qwen-local":
            await self.qwen.load()

    async def _unload(self, model_key: str) -> None:
        logger.info("Unloading model %s", model_key)
        if model_key == "llama-local":
            await self.llama.unload()
        elif model_key == "qwen-local":
            await self.qwen.unload()

    async def unload_all(self) -> None:
        async with self._lock:
            for key in list(self._loaded):
                await self._unload(key)
            self._loaded.clear()

    def local_available(self, model_key: str) -> bool:
        if model_key == "llama-local":
            return _model_files_present(self.settings.llama_model_path) and bool(
                detect_available_runtimes()
            )
        if model_key == "qwen-local":
            return _model_files_present(self.settings.qwen_model_path) and bool(
                detect_available_runtimes()
            )
        return False

    def external_available(self, model_id: str) -> bool:
        if model_id.startswith("openai:"):
            return self.openai.configured
        if model_id.startswith("gemini:"):
            return self.gemini.configured
        if model_id.startswith("claude:"):
            return self.claude.configured
        return False

    def status_for(self, model_id: str) -> str:
        if model_id in ("llama-local", "qwen-local"):
            if self.local_available(model_id):
                return "ok" if model_id in self._loaded or True else "ok"
            return "offline"
        if self.external_available(model_id):
            return "configured"
        return "not_configured"

    def list_models(self) -> list[dict[str, Any]]:
        from backend.config import load_model_capabilities

        caps = load_model_capabilities()
        result = []
        for mid, meta in caps.items():
            if mid.startswith("openai:") and not self.openai.configured:
                status = "not_configured"
            elif mid.startswith("gemini:") and not self.gemini.configured:
                status = "not_configured"
            elif mid.startswith("claude:") and not self.claude.configured:
                status = "not_configured"
            elif mid in ("llama-local", "qwen-local"):
                status = "ok" if self.local_available(mid) else "offline"
            else:
                status = "ok"
            location = "vps" if meta.get("local") else "api"
            indicator = "local" if meta.get("local") else "api"
            if status == "offline":
                indicator = "offline"
            result.append(
                {
                    "id": mid,
                    "name": meta.get("name"),
                    "display_location": meta.get("display_location"),
                    "location": location,
                    "indicator": indicator,
                    "status": status,
                    "capabilities": {
                        k: v
                        for k, v in meta.items()
                        if isinstance(v, bool)
                    },
                }
            )
        return result

    async def generate(self, model_id: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        if model_id == "llama-local":
            await self.ensure_loaded(model_id)
            return await self.llama.generate(messages, **kwargs)
        if model_id == "qwen-local":
            await self.ensure_loaded(model_id)
            return await self.qwen.generate(messages, **kwargs)
        if model_id.startswith("openai:"):
            return await self.openai.generate(model_id.split(":", 1)[1], messages, **kwargs)
        if model_id.startswith("gemini:"):
            return await self.gemini.generate(model_id.split(":", 1)[1], messages, **kwargs)
        if model_id.startswith("claude:"):
            return await self.claude.generate(model_id.split(":", 1)[1], messages, **kwargs)
        raise ValueError(f"Unknown model: {model_id}")

    async def stream(self, model_id: str, messages: list[dict[str, str]], **kwargs: Any):
        if model_id == "llama-local":
            await self.ensure_loaded(model_id)
            async for c in self.llama.stream(messages, **kwargs):
                yield c
            return
        if model_id == "qwen-local":
            await self.ensure_loaded(model_id)
            async for c in self.qwen.stream(messages, **kwargs):
                yield c
            return
        if model_id.startswith("openai:"):
            async for c in self.openai.stream(model_id.split(":", 1)[1], messages, **kwargs):
                yield c
            return
        if model_id.startswith("gemini:"):
            async for c in self.gemini.stream(model_id.split(":", 1)[1], messages, **kwargs):
                yield c
            return
        if model_id.startswith("claude:"):
            async for c in self.claude.stream(model_id.split(":", 1)[1], messages, **kwargs):
                yield c
            return
        raise ValueError(f"Unknown model: {model_id}")


_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
