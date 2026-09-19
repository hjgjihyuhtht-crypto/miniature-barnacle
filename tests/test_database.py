"""Database tests."""

import pytest

from backend.config import get_settings
from backend.database import init_db, close_db


@pytest.mark.asyncio
async def test_conversation_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    db = await init_db(get_settings())
    conv = await db.create_conversation("u", title="Teste", model="qwen-local", routing_mode="auto")
    await db.add_message(conv["id"], "user", "oi")
    await db.add_message(conv["id"], "assistant", "olá", model="qwen-local")
    msgs = await db.list_messages(conv["id"])
    assert len(msgs) == 2
    await db.record_usage("qwen-local", "local", True, latency_ms=12.5)
    await close_db()
    get_settings.cache_clear()
