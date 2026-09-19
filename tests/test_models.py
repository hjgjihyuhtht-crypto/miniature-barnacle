"""Model listing tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from backend.config import get_settings


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_API_KEY", "k")
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_models_capabilities(client):
    r = await client.get("/v1/models", headers={"Authorization": "Bearer k"})
    assert r.status_code == 200
    for m in r.json()["data"]:
        if m["id"] in ("llama-local", "qwen-local"):
            assert m["capabilities"]["vision"] is False
            assert m["capabilities"]["local"] is True
