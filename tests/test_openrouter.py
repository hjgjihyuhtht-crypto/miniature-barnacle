"""OpenRouter provider unit tests."""

import pytest

from backend.providers.openrouter import OpenRouterProvider, resolve_openrouter_model


def test_resolve_openrouter_models():
    assert resolve_openrouter_model("gpt-4o-mini") == "openai/gpt-4o-mini"
    assert resolve_openrouter_model("openai:gpt-4o") == "openai/gpt-4o"
    assert resolve_openrouter_model("gemini-2.0-flash") == "google/gemini-2.5-flash"
    assert resolve_openrouter_model("claude-sonnet-4-20250514") == "anthropic/claude-sonnet-4"
    assert resolve_openrouter_model("anthropic/claude-3.5-sonnet") == "anthropic/claude-3.5-sonnet"


@pytest.mark.asyncio
async def test_openrouter_not_configured():
    p = OpenRouterProvider("")
    assert p.configured is False
    with pytest.raises(RuntimeError):
        await p.generate("gpt-4o-mini", [{"role": "user", "content": "hi"}])
