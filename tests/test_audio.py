"""Audio / STT tests."""

import pytest

from backend.services.speech_to_text import NullSTTProvider, create_stt_provider
from backend.config import get_settings


@pytest.mark.asyncio
async def test_null_stt():
    p = NullSTTProvider()
    with pytest.raises(RuntimeError):
        await p.transcribe("/tmp/x.wav")
    h = await p.health()
    assert h["status"] == "not_configured"


def test_create_stt_auto(tmp_path, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "none")
    get_settings.cache_clear()
    p = create_stt_provider(get_settings())
    assert isinstance(p, NullSTTProvider)
    get_settings.cache_clear()
