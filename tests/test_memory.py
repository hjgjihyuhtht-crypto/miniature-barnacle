"""Memory system tests."""

import pytest

from backend.config import get_settings
from backend.database import init_db, close_db
from backend.memory.memory_manager import MemoryManager


@pytest.fixture
async def memory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "m.db"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    db = await init_db(get_settings())
    mm = MemoryManager(db=db, settings=get_settings())
    yield mm
    await close_db()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_memory_crud(memory):
    item = await memory.long.create("u1", "preference", "Prefiro respostas em português.", importance=0.8)
    assert item["id"]
    listed = await memory.long.list("u1")
    assert len(listed) == 1
    found = await memory.relevant_memories("u1", "qual idioma você usa?")
    assert isinstance(found, list)
    await memory.long.delete(item["id"])
    assert await memory.long.list("u1") == []


@pytest.mark.asyncio
async def test_suggest_not_trivia(memory):
    assert memory.suggest_memories("Qual a capital da França?") == []
    assert memory.suggest_memories("Prefiro respostas em português.") != []


@pytest.mark.asyncio
async def test_delete_all(memory):
    await memory.long.create("u1", "fact", "Meu projeto se chama NEXUS AI.")
    await memory.long.create("u1", "preference", "Prefiro português.")
    n = await memory.long.delete_all("u1")
    assert n == 2
