"""HTTP client for NEXUS backend (no provider keys on device)."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import httpx


class NexusAPIClient:
    def __init__(self, base_url: str, api_key: str, user_id: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user_id = user_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-User-Id": self.user_id,
        }

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/health")
            r.raise_for_status()
            return r.json()

    async def detailed_health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/v1/health", headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def list_models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
            r.raise_for_status()
            return r.json().get("data", [])

    async def choose_router(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/v1/router/choose",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    async def chat(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            if r.status_code >= 400:
                try:
                    detail = r.json()
                except Exception:
                    detail = {"detail": r.text}
                raise httpx.HTTPStatusError("chat failed", request=r.request, response=r)
            return r.json()

    async def chat_stream(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        payload = dict(payload)
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise RuntimeError(body.decode("utf-8", errors="ignore"))
                event_name = None
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("event: "):
                        event_name = line[7:].strip()
                        continue
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        yield {"event": event_name or "message", "data": obj}
                        event_name = None

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300) as client:
            files = {"file": open(audio_path, "rb")}
            data = {}
            if language:
                data["language"] = language
            try:
                r = await client.post(
                    f"{self.base_url}/v1/audio/transcriptions",
                    headers=self._headers(),
                    files=files,
                    data=data,
                )
                r.raise_for_status()
                return r.json()
            finally:
                files["file"].close()

    async def upload_attachment(self, path: str, conversation_id: Optional[str] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300) as client:
            files = {"file": open(path, "rb")}
            data = {}
            if conversation_id:
                data["conversation_id"] = conversation_id
            try:
                r = await client.post(
                    f"{self.base_url}/v1/attachments",
                    headers=self._headers(),
                    files=files,
                    data=data,
                )
                r.raise_for_status()
                return r.json()
            finally:
                files["file"].close()

    async def list_memory(self, q: Optional[str] = None) -> list[dict[str, Any]]:
        params = {"q": q} if q else None
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(
                f"{self.base_url}/v1/memory",
                headers=self._headers(),
                params=params,
            )
            r.raise_for_status()
            return r.json().get("data", [])

    async def create_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/v1/memory",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    async def delete_memory(self, memory_id: str) -> None:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.delete(
                f"{self.base_url}/v1/memory/{memory_id}",
                headers=self._headers(),
            )
            r.raise_for_status()

    async def delete_all_memory(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.delete(
                f"{self.base_url}/v1/memory",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()
