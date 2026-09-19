"""Google Gemini official API provider."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from backend.providers.base import ExternalProvider


class GeminiProvider(ExternalProvider):
    name = "gemini"

    def _url(self, model: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:{action}?key={self.api_key}"
        )

    def _payload(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        contents = []
        system_parts = []
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                system_parts.append(text)
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            },
        }
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        return body

    async def generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            resp = await client.post(
                self._url(model, stream=False),
                json=self._payload(messages, **kwargs),
            )
            resp.raise_for_status()
            data = resp.json()
        text = ""
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            text = ""
        usage_meta = data.get("usageMetadata") or {}
        usage = {}
        if "promptTokenCount" in usage_meta:
            usage["prompt_tokens"] = usage_meta.get("promptTokenCount")
        if "candidatesTokenCount" in usage_meta:
            usage["completion_tokens"] = usage_meta.get("candidatesTokenCount")
        if "totalTokenCount" in usage_meta:
            usage["total_tokens"] = usage_meta.get("totalTokenCount")
        return {"content": text, "usage": usage, "raw": data}

    async def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")
        url = self._url(model, stream=True) + "&alt=sse"
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 300)) as client:
            async with client.stream(
                "POST", url, json=self._payload(messages, **kwargs)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            yield text
                    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                        continue
