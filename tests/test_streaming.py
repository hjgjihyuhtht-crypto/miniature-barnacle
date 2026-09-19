"""Streaming helper tests."""

from backend.services.streaming import chat_chunk, sse_event


def test_sse_and_chunk():
    chunk = chat_chunk("qwen-local", "olá")
    assert chunk["choices"][0]["delta"]["content"] == "olá"
    event = sse_event({"a": 1}, event="router")
    assert event.startswith("event: router")
    assert "data: " in event
