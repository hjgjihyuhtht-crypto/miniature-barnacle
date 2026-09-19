"""Hugging Face Transformers runtime."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from backend.runtimes.base import LocalModelRuntime

logger = logging.getLogger("nexus.runtimes.transformers")


class TransformersRuntime(LocalModelRuntime):
    name = "transformers"

    def __init__(self, model_key: str, model_path: str, **kwargs: Any):
        super().__init__(model_key, model_path, **kwargs)
        self._model = None
        self._tokenizer = None
        self.model_id = kwargs.get("model_id") or model_path
        self.max_context = int(kwargs.get("n_ctx", 8192))
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
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            source = self._resolve_source()
            token = self.hf_token
            self._tokenizer = AutoTokenizer.from_pretrained(source, token=token)
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            self._model = AutoModelForCausalLM.from_pretrained(
                source,
                token=token,
                torch_dtype=dtype,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True,
            )
            if not torch.cuda.is_available():
                self._model.to("cpu")

        await asyncio.to_thread(_load)
        self._loaded = True
        logger.info("Loaded transformers model for %s", self.model_key)

    async def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._loaded = False
        try:
            import gc
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _apply_chat(self, messages: list[dict[str, str]]) -> str:
        assert self._tokenizer is not None
        if hasattr(self._tokenizer, "apply_chat_template"):
            return self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
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
            import torch

            assert self._model is not None and self._tokenizer is not None
            prompt = self._apply_chat(messages)
            inputs = self._tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-5),
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            new_tokens = output[0][inputs["input_ids"].shape[-1] :]
            text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
            return {
                "content": text,
                "usage": {
                    "prompt_tokens": int(inputs["input_ids"].shape[-1]),
                    "completion_tokens": int(new_tokens.shape[-1]),
                    "total_tokens": int(inputs["input_ids"].shape[-1] + new_tokens.shape[-1]),
                },
            }

        return await asyncio.to_thread(_gen)

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        if not self._loaded:
            await self.load()
        max_tokens = int(kwargs.get("max_tokens", 2048))
        temperature = float(kwargs.get("temperature", 0.7))
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _stream() -> None:
            try:
                from threading import Thread

                from transformers import TextIteratorStreamer

                assert self._model is not None and self._tokenizer is not None
                prompt = self._apply_chat(messages)
                inputs = self._tokenizer(prompt, return_tensors="pt")
                inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
                streamer = TextIteratorStreamer(
                    self._tokenizer, skip_prompt=True, skip_special_tokens=True
                )
                gen_kwargs = dict(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-5),
                    pad_token_id=self._tokenizer.eos_token_id,
                    streamer=streamer,
                )
                thread = Thread(target=self._model.generate, kwargs=gen_kwargs)
                thread.start()
                for text in streamer:
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
                thread.join()
            except Exception as exc:
                logger.exception("transformers stream error: %s", exc)
                try:
                    import torch

                    assert self._model is not None and self._tokenizer is not None
                    prompt = self._apply_chat(messages)
                    inputs = self._tokenizer(prompt, return_tensors="pt")
                    inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
                    with torch.no_grad():
                        output = self._model.generate(
                            **inputs,
                            max_new_tokens=max_tokens,
                            do_sample=temperature > 0,
                            temperature=max(temperature, 1e-5),
                            pad_token_id=self._tokenizer.eos_token_id,
                        )
                    new_tokens = output[0][inputs["input_ids"].shape[-1] :]
                    text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
                except Exception:
                    logger.exception("transformers fallback generate failed")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(asyncio.to_thread(_stream))
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    async def health(self) -> dict[str, Any]:
        path = Path(self.model_path)
        return {
            "runtime": self.name,
            "loaded": self._loaded,
            "path_exists": path.exists(),
            "source": self._resolve_source(),
        }
