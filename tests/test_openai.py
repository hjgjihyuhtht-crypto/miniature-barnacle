"""OpenAI provider unit tests (no real network if not configured)."""

import pytest

from backend.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_not_configured():
    p = OpenAIProvider("")
    assert p.configured is False
    with pytest.raises(RuntimeError):
        await p.generate("gpt-4o-mini", [{"role": "user", "content": "hi"}])
