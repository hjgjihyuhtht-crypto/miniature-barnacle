"""Streaming helpers for the Flet client."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Optional

from app.services.api_client import NexusAPIClient


async def stream_chat(
    client: NexusAPIClient,
    payload: dict[str, Any],
    on_router: Optional[Callable[[dict], None]] = None,
    on_token: Optional[Callable[[str], None]] = None,
) -> str:
    full = []
    async for event in client.chat_stream(payload):
        name = event.get("event")
        data = event.get("data") or {}
        if name == "router" and on_router:
            on_router(data)
        elif name == "error":
            raise RuntimeError(data.get("error") or str(data))
        else:
            choices = data.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                token = delta.get("content") or ""
                if token:
                    full.append(token)
                    if on_token:
                        on_token(token)
    return "".join(full)
