"""Gemini provider unit tests."""

import pytest

from backend.providers.gemini import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_not_configured():
    p = GeminiProvider("")
    assert (await p.health())["status"] == "not_configured"
    with pytest.raises(RuntimeError):
        await p.generate("gemini-2.0-flash", [{"role": "user", "content": "hi"}])
