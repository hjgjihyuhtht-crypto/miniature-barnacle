"""OpenRouter OpenAI-compatible gateway for all external API models."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from backend.providers.base import ExternalProvider

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# NEXUS short names / vendor ids → OpenRouter model slugs
MODEL_MAP: dict[str, str] = {
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4o": "openai/gpt-4o",
    "gemini-2.0-flash": "google/gemini-2.5-flash",
    "gemini-2.0-flash-001": "google/gemini-2.5-flash",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "claude-sonnet-4-20250514": "anthropic/claude-sonnet-4",
    "claude-sonnet-4": "anthropic/claude-sonnet-4",
}


def resolve_openrouter_model(model: str) -> str:
    """Map NEXUS / vendor model ids to OpenRouter slugs."""
    raw = (model or "").strip()
    if not raw:
        raise ValueError("model id required")
    # Strip NEXUS prefixes (openai:gpt-4o → gpt-4o)
    if ":" in raw and "/" not in raw.split(":", 1)[0]:
        raw = raw.split(":", 1)[1]
    if raw in MODEL_MAP:
        return MODEL_MAP[raw]
    # Already an OpenRouter slug (vendor/model)
    if "/" in raw:
        return raw
    return raw


class OpenRouterProvider(ExternalProvider):
    """Single key → OpenAI, Gemini, Claude (and more) via OpenRouter."""

    name = "openrouter"

    def __init__(self, api_key: str, name: str | None = None):
        super().__init__(api_key)
        if name:
            self.name = name

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nexus-ai.local",
            "X-Title": "NEXUS AI",
        }

    async def generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("OpenRouter API key not configured")
        payload = {
            "model": resolve_openrouter_model(model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
            "raw": data,
        }

    async def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self.configured:
            raise RuntimeError("OpenRouter API key not configured")
        payload = {
            "model": resolve_openrouter_model(model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            async with client.stream(
                "POST", OPENROUTER_URL, json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        text = delta.get("content")
                        if text:
                            yield text
