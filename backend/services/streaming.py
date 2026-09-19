"""SSE streaming helpers."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Optional


def sse_event(data: dict[str, Any], event: Optional[str] = None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


def chat_chunk(model: str, content: str, finish_reason: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }


async def stream_tokens(
    token_iter: AsyncIterator[str],
    model: str,
    meta: Optional[dict[str, Any]] = None,
) -> AsyncIterator[str]:
    if meta:
        yield sse_event(meta, event="router")
    async for token in token_iter:
        yield sse_event(chat_chunk(model, token))
    yield sse_event(chat_chunk(model, "", finish_reason="stop"))
    yield "data: [DONE]\n\n"
