"""Anthropic Claude official API provider."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from backend.providers.base import ExternalProvider

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class ClaudeProvider(ExternalProvider):
    name = "claude"

    async def generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Anthropic API key not configured")
        system = None
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = (system + "\n" if system else "") + m.get("content", "")
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})
        payload: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
        }
        if system:
            payload["system"] = system
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            resp = await client.post(ANTHROPIC_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        usage_raw = data.get("usage") or {}
        usage = {}
        if "input_tokens" in usage_raw:
            usage["prompt_tokens"] = usage_raw["input_tokens"]
        if "output_tokens" in usage_raw:
            usage["completion_tokens"] = usage_raw["output_tokens"]
        if usage.get("prompt_tokens") is not None and usage.get("completion_tokens") is not None:
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        return {"content": text, "usage": usage, "raw": data}

    async def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self.configured:
            raise RuntimeError("Anthropic API key not configured")
        system = None
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = (system + "\n" if system else "") + m.get("content", "")
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})
        payload: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
        }
        if system:
            payload["system"] = system
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            async with client.stream("POST", ANTHROPIC_URL, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta") or {}
                        text = delta.get("text")
                        if text:
                            yield text
