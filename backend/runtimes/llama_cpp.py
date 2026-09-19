"""llama.cpp / GGUF runtime."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from backend.runtimes.base import LocalModelRuntime

logger = logging.getLogger("nexus.runtimes.llama_cpp")


def _find_gguf(model_path: str) -> Path | None:
    path = Path(model_path)
    if path.is_file() and path.suffix.lower() == ".gguf":
        return path
    if path.is_dir():
        files = sorted(path.glob("**/*.gguf"))
        return files[0] if files else None
    return None


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"<|{role}|>\n{content}")
    parts.append("<|assistant|>\n")
    return "\n".join(parts)


class LlamaCppRuntime(LocalModelRuntime):
    name = "llama_cpp"

    def __init__(self, model_key: str, model_path: str, **kwargs: Any):
        super().__init__(model_key, model_path, **kwargs)
        self._llm = None
        self.n_ctx = int(kwargs.get("n_ctx", 8192))
        self.n_threads = int(kwargs.get("n_threads", 4))
        self.n_gpu_layers = int(kwargs.get("n_gpu_layers", 0))

    async def load(self) -> None:
        if self._loaded:
            return

        def _load() -> None:
            from llama_cpp import Llama

            gguf = _find_gguf(self.model_path)
            if not gguf:
                raise FileNotFoundError(
                    f"No GGUF file found under {self.model_path}. "
                    "Download a compatible GGUF or switch LOCAL_RUNTIME=transformers."
                )
            self._llm = Llama(
                model_path=str(gguf),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )

        await asyncio.to_thread(_load)
        self._loaded = True
        logger.info("Loaded llama.cpp model for %s", self.model_key)

    async def unload(self) -> None:
        self._llm = None
        self._loaded = False

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        if not self._loaded:
            await self.load()
        prompt = _messages_to_prompt(messages)
        max_tokens = int(kwargs.get("max_tokens", 2048))
        temperature = float(kwargs.get("temperature", 0.7))

        def _gen() -> dict[str, Any]:
            assert self._llm is not None
            out = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["<|user|>", "<|system|>"],
            )
            text = out["choices"][0]["text"]
            usage = out.get("usage") or {}
            return {
                "content": text,
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
            }

        return await asyncio.to_thread(_gen)

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        if not self._loaded:
            await self.load()
        prompt = _messages_to_prompt(messages)
        max_tokens = int(kwargs.get("max_tokens", 2048))
        temperature = float(kwargs.get("temperature", 0.7))
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _stream() -> None:
            assert self._llm is not None
            try:
                stream = self._llm(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|user|>", "<|system|>"],
                    stream=True,
                )
                for chunk in stream:
                    text = chunk["choices"][0]["text"]
                    if text:
                        asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, text)
            finally:
                asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, None)

        loop = asyncio.get_running_loop()
        # Use a bridge that works across threads
        def _stream_safe() -> None:
            assert self._llm is not None
            try:
                stream = self._llm(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|user|>", "<|system|>"],
                    stream=True,
                )
                for chunk in stream:
                    text = chunk["choices"][0]["text"]
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as exc:
                logger.exception("llama.cpp stream error: %s", exc)
                loop.call_soon_threadsafe(queue.put_nowait, None)
                return
            loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(asyncio.to_thread(_stream_safe))
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    async def health(self) -> dict[str, Any]:
        gguf = _find_gguf(self.model_path)
        return {
            "runtime": self.name,
            "loaded": self._loaded,
            "gguf_found": gguf is not None,
            "path": str(gguf) if gguf else self.model_path,
        }
