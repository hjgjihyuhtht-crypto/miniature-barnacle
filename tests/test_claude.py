"""Claude provider unit tests."""

import pytest

from backend.providers.claude import ClaudeProvider


@pytest.mark.asyncio
async def test_claude_not_configured():
    p = ClaudeProvider("")
    assert p.configured is False
    with pytest.raises(RuntimeError):
        await p.generate("claude-sonnet-4-20250514", [{"role": "user", "content": "hi"}])
